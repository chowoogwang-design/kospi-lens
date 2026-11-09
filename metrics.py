"""Valuation and point-in-time statement parsing for the Korean equity screener."""
from __future__ import annotations

import datetime as dt
import re
from typing import Any

REPORT_NAMES = {"11011": "FY", "11013": "Q1", "11012": "H1", "11014": "9M"}
QUARTER_CODES = ("11014", "11012", "11013")
ASSETS_IDS = ("ifrs-full_Assets", "ifrs_Assets")
GROUP_EQUITY_IDS = ("ifrs-full_Equity", "ifrs_Equity")
OWNER_EQUITY_IDS = (
    "ifrs-full_EquityAttributableToOwnersOfParent",
    "ifrs_EquityAttributableToOwnersOfParent",
)
OWNER_PROFIT_IDS = (
    "ifrs-full_ProfitLossAttributableToOwnersOfParent",
    "ifrs_ProfitLossAttributableToOwnersOfParent",
)
SINGLE_PROFIT_IDS = ("ifrs-full_ProfitLoss", "ifrs_ProfitLoss")


def number(raw: Any) -> int | None:
    if raw is None or isinstance(raw, bool):
        return None
    if isinstance(raw, (int, float)):
        return int(raw)
    val = str(raw).strip().replace(",", "").replace(" ", "")
    if val in ("", "-", "N/A", "null"):
        return None
    if val.startswith("(") and val.endswith(")"):
        val = "-" + val[1:-1]
    try:
        return int(float(val))
    except (ValueError, OverflowError):
        return None


def period_end(text: str) -> str | None:
    matches = re.findall(r"(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})", text or "")
    if not matches:
        return None
    year, month, day = matches[-1]
    try:
        return dt.date(int(year), int(month), int(day)).isoformat()
    except ValueError:
        return None


def is_parent_profit(row: dict) -> bool:
    account = row.get("account_id", "")
    name = re.sub(r"\s", "", row.get("account_nm", ""))
    return account in OWNER_PROFIT_IDS or (
        "지배기업" in name and "순이익" in name and "비지배" not in name
    )


def extract_statement(rows: list[dict], year: int, code: str) -> dict | None:
    """Choose CFS if present; OFS only if a consolidated report is unavailable.

    Do not substitute group net income or group equity for the parent attributable
    figures. Missing parent figures remain null instead of quietly biasing P/E/P/B.
    """
    if not rows:
        return None
    # A small number of reporters use non-KRW presentation currencies;
    # never silently interpret USD or other currencies as won.
    valid = [r for r in rows if r.get("sj_div") in ("BS", "IS", "CIS")
             and str(r.get("currency") or "KRW").upper() in ("KRW", "원", "대한민국원")]
    fs_div = "CFS" if any(r.get("fs_div") == "CFS" for r in valid) else "OFS"
    matched = [r for r in valid if r.get("fs_div") == fs_div]

    def choose(statement_types: tuple[str, ...], ids: tuple[str, ...], names: tuple[str, ...] = (), owner=False):
        pool = [r for r in matched if r.get("sj_div") in statement_types]
        for a in ids:
            for r in pool:
                if r.get("account_id") == a:
                    return r
        for n in names:
            for r in pool:
                if re.sub(r"\s", "", r.get("account_nm", "")) == n:
                    return r
        if owner:
            for r in pool:
                if is_parent_profit(r):
                    return r
        return None

    assets_r = choose(("BS",), ASSETS_IDS, ("자산총계",))
    equity_r = (choose(("BS",), OWNER_EQUITY_IDS, ("지배기업소유주지분", "지배기업의소유주에게귀속되는자본"))
                if fs_div == "CFS" else choose(("BS",), GROUP_EQUITY_IDS, ("자본총계",)))
    profit_r = (choose(("IS", "CIS"), OWNER_PROFIT_IDS, owner=True)
                if fs_div == "CFS" else choose(("IS", "CIS"), SINGLE_PROFIT_IDS, ("당기순이익", "분기순이익", "반기순이익")))

    def val(row, is_profit=False):
        if row is None:
            return None
        if is_profit and code != "11011":
            # Quarterly "thstrm_amount" is the 3-month figure. We need YTD.
            return number(row.get("thstrm_add_amount"))
        return number(row.get("thstrm_amount"))

    dates = [period_end(r.get("thstrm_dt", "")) for r in (assets_r, equity_r, profit_r) if r]
    dates = [d for d in dates if d]
    return {
        "year": year, "code": code, "label": f"{year} {REPORT_NAMES[code]}",
        "as_of": max(dates) if dates else None,
        "basis": "Consolidated" if fs_div == "CFS" else "Separate (no CFS)",
        "assets": val(assets_r), "equity_parent": val(equity_r),
        "net_income_parent_ytd": val(profit_r, is_profit=True),
        "receipt_no": next((r.get("rcept_no") for r in matched if r.get("rcept_no")), None),
    }


def calculate_financials(reports: dict[tuple[int, str], dict], as_of_year: int) -> dict | None:
    """Compute LTM = last annual FY + current YTD - prior-year same YTD.

    For an issuer with no new interim statement, FY earnings are valid but
    labelled FY rather than LTM. Unsupported or nonpositive earnings => no P/E.
    """
    candidates = [(y, code) for y in range(as_of_year, as_of_year - 3, -1)
                  for code in ("11011", *QUARTER_CODES)]
    latest = next((reports[k] for k in candidates if k in reports and reports[k].get("assets") is not None), None)
    if not latest:
        return None
    latest_key = (latest["year"], latest["code"])
    assets = latest.get("assets")
    equity = latest.get("equity_parent")
    earnings = None
    income_label = None
    income_basis = None
    if latest["code"] == "11011":
        earnings = latest.get("net_income_parent_ytd")
        income_label = latest["label"]
        income_basis = "FY"
    else:
        year, q_code = latest_key
        previous_fy = reports.get((year - 1, "11011"))
        prior_ytd = reports.get((year - 1, q_code))
        if previous_fy and prior_ytd and all(
            r.get("net_income_parent_ytd") is not None
            for r in (latest, previous_fy, prior_ytd)
        ) and latest["basis"] == previous_fy["basis"] == prior_ytd["basis"]:
            earnings = (previous_fy["net_income_parent_ytd"]
                        + latest["net_income_parent_ytd"]
                        - prior_ytd["net_income_parent_ytd"])
            income_label = f"LTM to {latest['label']} (FY{year-1} + {year} {REPORT_NAMES[q_code]} - {year-1} {REPORT_NAMES[q_code]})"
            income_basis = "LTM"
    return {
        "assets_krw": assets, "equity_krw": equity, "earnings_krw": earnings,
        "report_period": latest["label"], "report_date": latest.get("as_of"),
        "statement_basis": latest["basis"],
        "earnings_period": income_label, "earnings_basis": income_basis,
        "dart_receipt": latest.get("receipt_no"),
    }


def valuation(market_cap_krw: int | None, finances: dict | None) -> tuple[float | None, float | None]:
    if not finances or not market_cap_krw or market_cap_krw <= 0:
        return None, None
    income = finances.get("earnings_krw")
    equity = finances.get("equity_krw")
    pe = round(market_cap_krw / income, 2) if income is not None and income > 0 else None
    pb = round(market_cap_krw / equity, 2) if equity is not None and equity > 0 else None
    return pe, pb
