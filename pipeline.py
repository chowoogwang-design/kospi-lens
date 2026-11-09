"""KRX daily market snapshot + OpenDART filings. Run: python -m app.refresh --live.

Intentional constraints:
- No fake live data or third-party HTML scraping.
- Financial statements are taken from their stated fiscal periods; no look-ahead.
- Parent-attributable income/equity are used for consolidated issuers.
- Market cap is common listed class only, so valuation is indicative for
  issuers with separately listed preferred shares.
"""
from __future__ import annotations

import concurrent.futures
import datetime as dt
import io
import json
import os
import pathlib
import time
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from typing import Any

import requests
from zoneinfo import ZoneInfo

from .industry import classify
from .metrics import calculate_financials, extract_statement, number, valuation

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA_DIR = pathlib.Path(os.environ.get("KOSPI_DATA_DIR", str(ROOT / "data"))).expanduser().resolve()
CACHE_DIR = DATA_DIR / "cache"
SNAPSHOT = DATA_DIR / "snapshot.json"
KST = ZoneInfo("Asia/Seoul")
DART = "https://opendart.fss.or.kr/api"
KRX_DAILY = "https://data-dbg.krx.co.kr/svc/apis/sto/stk_bydd_trd"
REPORTS = ("11011", "11014", "11012", "11013")


@dataclass
class Credentials:
    krx: str
    dart: str


class ProviderError(RuntimeError):
    pass


def atomic_json(path: pathlib.Path, data: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    target = path.with_suffix(path.suffix + ".tmp")
    target.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    target.replace(path)


def read_json(path: pathlib.Path) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return None


def dart_json(session, key, endpoint, params):
    r = session.get(f"{DART}/{endpoint}.json", params={"crtfc_key": key, **params}, timeout=35)
    r.raise_for_status()
    obj = r.json()
    status = obj.get("status")
    if status == "013":  # OpenDART: no data
        return []
    if status != "000":
        raise ProviderError(f"OpenDART {endpoint}: {status}: {obj.get('message')}")
    return obj.get("list", obj)


def request_krx(session, key, day: dt.date):
    payload = {"basDd": day.strftime("%Y%m%d")}
    headers = {"AUTH_KEY": key, "Content-Type": "application/json"}
    # KRX environments/documentation differ regarding query vs JSON body;
    # try POST first and GET fallback when rejected.
    methods = (
        lambda: session.post(KRX_DAILY, json=payload, headers=headers, timeout=35),
        lambda: session.get(KRX_DAILY, params=payload, headers={"AUTH_KEY": key}, timeout=35),
    )
    last_error = None
    for make_request in methods:
        try:
            r = make_request()
            r.raise_for_status()
            data = r.json()
            rows = data.get("OutBlock_1")
            if not isinstance(rows, list):
                last_error = f"KRX returned no OutBlock_1: {str(data)[:160]}"
                continue
            return rows
        except (requests.RequestException, ValueError) as exc:
            last_error = str(exc)
    raise ProviderError(f"KRX request failed: {last_error}")


def fetch_latest_krx(session, key, today=None):
    day = today or dt.datetime.now(KST).date()
    # Search up to 12 days back, covering long holiday periods.
    for back in range(0, 13):
        target = day - dt.timedelta(days=back)
        if target.weekday() >= 5:
            continue
        rows = request_krx(session, key, target)
        if rows:
            return target.isoformat(), rows
    raise ProviderError("KRX returned no daily equity session within 13 calendar days")


def corp_directory(session, key):
    path = CACHE_DIR / "corp_directory.json"
    cached = read_json(path)
    if cached and (time.time() - cached.get("fetched", 0)) < 7 * 86400:
        return cached["records"]
    response = session.get(f"{DART}/corpCode.xml", params={"crtfc_key": key}, timeout=100)
    response.raise_for_status()
    try:
        with zipfile.ZipFile(io.BytesIO(response.content)) as package:
            xml = package.read(package.namelist()[0])
        root = ET.fromstring(xml)
    except (ValueError, zipfile.BadZipFile, ET.ParseError) as exc:
        raise ProviderError(f"Could not read DART corpCode ZIP: {exc}") from exc
    mapping = {}
    for company in root.findall(".//list"):
        ticker = company.findtext("stock_code", default="").strip()
        if len(ticker) == 6 and ticker.isdigit():
            mapping[ticker] = {
                "corp_code": company.findtext("corp_code", default=""),
                "corp_name": company.findtext("corp_name", default=""),
            }
    atomic_json(path, {"fetched": time.time(), "records": mapping})
    return mapping


def report_candidates(today: dt.date):
    # If a later report is not filed, DART status 013 permits graceful fall back.
    # For each fiscal year, FY outranks its quarterly reports.
    years = (today.year, today.year - 1, today.year - 2)
    return [(year, code) for year in years for code in REPORTS]


def fetch_bulk_assets(session, key, corp_by_ticker, today):
    """Batch major accounts, to screen out sub-200bn issuers cheaply."""
    reverse = {v["corp_code"]: t for t, v in corp_by_ticker.items()}
    codes = list(reverse)
    results = {}
    for year, rep_code in report_candidates(today):
        if len(results) == len(codes):
            break
        remaining = [code for code in codes if code not in results]
        for start in range(0, len(remaining), 50):
            chunk = remaining[start:start + 50]
            rows = dart_json(session, key, "fnlttMultiAcnt", {
                "corp_code": ",".join(chunk), "bsns_year": str(year), "reprt_code": rep_code,
            })
            for item in rows:
                if (item.get("sj_div") != "BS"
                    or str(item.get("account_nm", "")).replace(" ", "") != "자산총계"):
                    continue
                if str(item.get("currency") or "KRW").upper() not in ("KRW", "원", "대한민국원"):
                    continue
                corp = item.get("corp_code")
                # The bulk API sometimes supplies stock_code, sometimes corp_code.
                ticker = item.get("stock_code") or reverse.get(corp)
                if ticker not in corp_by_ticker:
                    continue
                val = number(item.get("thstrm_amount"))
                if val is None:
                    continue
                existing = results.get(ticker)
                # Prefer consolidated rows regardless of order within the same period.
                if existing is None or (existing["period"] == (year, rep_code)
                                         and existing.get("fs_div") != "CFS" and item.get("fs_div") == "CFS"):
                    results[ticker] = {"assets": val, "period": (year, rep_code),
                                       "fs_div": item.get("fs_div")}
    return results


def cached_report(session, key, corp_code, year, rep_code, now):
    path = CACHE_DIR / "statements" / f"{corp_code}_{year}_{rep_code}.json"
    stored = read_json(path)
    # Fresh/current reports rechecked every day for filings/amendments; historical
    # reports are rechecked weekly to capture revisions without hammering DART.
    ttl = 86400 if year >= now.year - 1 else 7 * 86400
    if stored and time.time() - stored.get("fetched", 0) < ttl:
        return stored.get("rows", [])
    rows = dart_json(session, key, "fnlttSinglAcntAll", {
        "corp_code": corp_code, "bsns_year": str(year),
        "reprt_code": rep_code, "fs_div": "CFS",
    })
    # DART CFS missing when issuer files only separate statements.
    if not rows:
        rows = dart_json(session, key, "fnlttSinglAcntAll", {
            "corp_code": corp_code, "bsns_year": str(year),
            "reprt_code": rep_code, "fs_div": "OFS",
        })
    atomic_json(path, {"fetched": time.time(), "rows": rows})
    return rows


def fetch_issuer_financials(session, key, issuer, today):
    corp = issuer["corp_code"]
    reports = {}
    # Current year, previous year and FY two years ago support per-issuer
    # fallback plus LTM (FY + current YTD - previous YTD).
    for year, code in report_candidates(today):
        # Can't have published FY for the current fiscal year until next year;
        # skip obviously unavailable periods, not early-filed quarterlies.
        if year == today.year and code == "11011":
            continue
        if year == today.year - 2 and code != "11011":
            continue
        rows = cached_report(session, key, corp, year, code, today)
        st = extract_statement(rows, year, code)
        if st and st["assets"] is not None:
            reports[(year, code)] = st
        # Once current interim data, previous FY and corresponding prior YTD
        # exist, the remaining older quarters are unnecessary.
        current = [r for (y, c), r in reports.items() if y == today.year and c != "11011"]
        if current:
            latest_c = sorted(current, key=lambda r: REPORTS.index(r["code"]))[0]["code"]
            if ((today.year - 1, "11011") in reports
                    and (today.year - 1, latest_c) in reports):
                break
        if (today.year - 1, "11011") in reports and not current and year <= today.year - 1:
            # We still need not go backwards if last FY is all that is filed.
            # Do not break until all current q alternatives have been checked.
            break
    return calculate_financials(reports, today.year)


def fetch_company_meta(session, key, ticker, corp_code):
    # Shared cache is loaded/written by the orchestrator, not workers.
    obj = dart_json(session, key, "company", {"corp_code": corp_code})
    # 'company.json' is an object, not a 'list'.
    if isinstance(obj, list):
        return {}
    return {"industry_code": obj.get("induty_code"), "name_en": obj.get("corp_name_eng")}


def normalize_krx_rows(raw, day):
    items = {}
    for item in raw:
        ticker = str(item.get("ISU_CD", "")).strip()
        if len(ticker) != 6 or not ticker.isdigit():
            continue
        price = number(item.get("TDD_CLSPRC"))
        mcap = number(item.get("MKTCAP"))
        if not price or not mcap or price < 0 or mcap <= 0:
            continue
        items[ticker] = {
            "ticker": ticker, "name": item.get("ISU_NM") or ticker,
            "price": price, "volume": number(item.get("ACC_TRDVOL")),
            "market_cap_krw": mcap, "change_pct": float(str(item.get("FLUC_RT") or "0").replace(",", "")),
            "price_date": day,
        }
    return items


def build_live_snapshot(keys: Credentials, max_companies=None, on_progress=print):
    DATA_DIR.mkdir(exist_ok=True, parents=True)
    CACHE_DIR.mkdir(exist_ok=True, parents=True)
    with requests.Session() as session:
        today = dt.datetime.now(KST).date()
        day, raw_quotes = fetch_latest_krx(session, keys.krx, today=today)
        stocks = normalize_krx_rows(raw_quotes, day)
        on_progress(f"KRX: {len(stocks)} stock-class quotes on {day}")
        directory = corp_directory(session, keys.dart)
        issuers = {ticker: directory[ticker] for ticker in stocks if ticker in directory}
        on_progress(f"DART: {len(issuers)} listed issuer codes matched")
        assets = fetch_bulk_assets(session, keys.dart, issuers, today)
        eligible = [t for t, a in assets.items() if a["assets"] > 200_000_000_000]
        eligible.sort(key=lambda t: stocks[t]["market_cap_krw"], reverse=True)
        if max_companies:
            eligible = eligible[:max_companies]
        on_progress(f"Assets > KRW 200bn: {len(eligible)} companies; fetching full statement periods")

        # Cached meta enrichment avoids refetching ~hundreds of company profiles daily.
        meta_path = CACHE_DIR / "company_meta.json"
        meta_cache = read_json(meta_path) or {}
        output = []
        errors = []

        def enrich(ticker):
            issuer = issuers[ticker]
            own_session = requests.Session()
            try:
                financial = fetch_issuer_financials(own_session, keys.dart, issuer, today)
                if financial is None:
                    return (ticker, None, None, "missing financial statements")
                if ticker in meta_cache:
                    meta = meta_cache[ticker]
                else:
                    meta = fetch_company_meta(own_session, keys.dart, ticker, issuer["corp_code"])
                return (ticker, financial, meta, None)
            except Exception as exc:
                return (ticker, None, None, str(exc))
            finally:
                own_session.close()

        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            for idx, (ticker, financial, meta, error) in enumerate(pool.map(enrich, eligible), 1):
                if error:
                    errors.append(f"{ticker}: {error}")
                    continue
                if financial["assets_krw"] is None or financial["assets_krw"] <= 200_000_000_000:
                    continue
                meta_cache[ticker] = meta or {}
                quote = stocks[ticker]
                sector, industry = classify((meta or {}).get("industry_code"))
                pe, pb = valuation(quote["market_cap_krw"], financial)
                output.append({
                    **quote, "name_en": (meta or {}).get("name_en") or "",
                    "market_cap_bn": round(quote["market_cap_krw"] / 1e9, 3),
                    "sector": sector, "industry": industry,
                    "industry_code": (meta or {}).get("industry_code"),
                    "assets_bn": round(financial["assets_krw"] / 1e9, 3),
                    "equity_bn": round(financial["equity_krw"] / 1e9, 3) if financial["equity_krw"] is not None else None,
                    "earnings_bn": round(financial["earnings_krw"] / 1e9, 3) if financial["earnings_krw"] is not None else None,
                    "pe": pe, "pb": pb,
                    "report_period": financial["report_period"], "report_date": financial["report_date"],
                    "earnings_period": financial["earnings_period"],
                    "earnings_basis": financial["earnings_basis"],
                    "statement_basis": financial["statement_basis"],
                    "dart_receipt": financial["dart_receipt"],
                    "naver_url": f"https://finance.naver.com/item/main.naver?code={ticker}",
                })
                if idx % 50 == 0:
                    atomic_json(meta_path, meta_cache)
                    on_progress(f"Processed {idx}/{len(eligible)}")
        atomic_json(meta_path, meta_cache)
        if errors:
            (DATA_DIR / "last_refresh_errors.log").write_text("\n".join(errors), encoding="utf-8")
            on_progress(f"Warning: {len(errors)} companies could not be enriched; see data/last_refresh_errors.log")
        if not output:
            raise ProviderError("No eligible companies enriched. Previous snapshot kept intact.")
        output.sort(key=lambda r: r["market_cap_bn"], reverse=True)
        result = {
            "mode": "live", "notice": None,
            "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "price_date": day, "asset_threshold_bn": 200,
            "total_krx_stocks": len(stocks),
            "missing_financials": len(issuers) - len(assets),
            "failed_enrichment": len(errors),
            "partial": bool(max_companies or errors),
            "companies": output,
        }
        atomic_json(SNAPSHOT, result)
        on_progress(f"Saved {len(output)} eligible companies to {SNAPSHOT}")
        return result
