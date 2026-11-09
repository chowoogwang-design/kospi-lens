"""Explicitly fictional demo figures. They are NOT current market data."""
from __future__ import annotations

from datetime import datetime, timezone

# Names / tickers are identifying labels; all amounts, prices and multiples are
# deliberately generated examples and must never be treated as actual quotes.
ROWS = [
    ("005930", "삼성전자", "Samsung Electronics", "Information Technology", "Electronics & semiconductors", 78500, 12854031, 466852, 455906, 352800, 35620, 2.1),
    ("000660", "SK하이닉스", "SK Hynix", "Information Technology", "Electronics & semiconductors", 191000, 3120411, 139048, 126840, 82600, 21000, -0.7),
    ("005380", "현대차", "Hyundai Motor", "Consumer Discretionary", "Automobiles", 224000, 874932, 47120, 282463, 125200, 10500, 1.4),
    ("000270", "기아", "Kia", "Consumer Discretionary", "Automobiles", 100200, 1123930, 40080, 91232, 51240, 8480, -1.1),
    ("105560", "KB금융", "KB Financial Group", "Financials", "Financial services", 83200, 921300, 33050, 715240, 64000, 5540, 0.3),
    ("055550", "신한지주", "Shinhan Financial Group", "Financials", "Financial services", 57400, 1012300, 27810, 665321, 56000, 4400, 1.8),
    ("035420", "NAVER", "NAVER", "Communication Services", "Information services", 213000, 594000, 34060, 39000, 25830, 1750, -0.3),
    ("035720", "카카오", "Kakao", "Communication Services", "Information services", 41900, 1471500, 18600, 25400, 16500, 620, 2.5),
    ("207940", "삼성바이오로직스", "Samsung Biologics", "Health Care", "Pharmaceuticals & biotechnology", 990000, 85721, 70420, 15120, 10240, 890, 0.5),
    ("068270", "셀트리온", "Celltrion", "Health Care", "Pharmaceuticals & biotechnology", 177000, 345771, 38420, 20020, 16100, 850, -1.4),
    ("005490", "POSCO홀딩스", "POSCO Holdings", "Materials", "Primary metals", 330000, 431520, 26840, 101060, 56530, 2500, 1.1),
    ("051910", "LG화학", "LG Chem", "Materials", "Chemicals", 358000, 308000, 25210, 72400, 32500, -890, -1.9),
    ("373220", "LG에너지솔루션", "LG Energy Solution", "Industrials", "Electrical equipment", 398000, 117920, 93100, 46400, 27000, 250, 0.1),
    ("006400", "삼성SDI", "Samsung SDI", "Industrials", "Electrical equipment", 370000, 281207, 25400, 34400, 21500, -530, -2.0),
    ("012330", "현대모비스", "Hyundai Mobis", "Consumer Discretionary", "Automobiles", 248000, 190843, 22960, 65000, 43000, 3190, 1.6),
    ("003550", "LG", "LG Corp", "Industrials", "Conglomerates", 85000, 194258, 13300, 33000, 25500, 1400, 0.2),
    ("086790", "하나금융지주", "Hana Financial Group", "Financials", "Financial services", 65800, 643190, 19750, 630000, 41500, 4000, -0.5),
    ("316140", "우리금융지주", "Woori Financial Group", "Financials", "Financial services", 16700, 1675300, 12640, 545000, 34000, 3140, 1.9),
    ("015760", "한국전력", "KEPCO", "Utilities", "Electricity & utilities", 25900, 2740930, 16620, 235000, 52000, 3600, -0.8),
    ("000810", "삼성화재", "Samsung Fire & Marine", "Financials", "Insurance", 362000, 72280, 17100, 92000, 21500, 1900, 0.6),
    ("034730", "SK", "SK Inc", "Industrials", "Conglomerates", 177000, 105244, 12000, 203000, 49000, 4000, -0.1),
    ("090430", "아모레퍼시픽", "Amorepacific", "Consumer Staples", "Consumer products", 144000, 133800, 8550, 7300, 4800, 180, 0.8),
    ("004020", "현대제철", "Hyundai Steel", "Materials", "Primary metals", 29600, 380340, 3950, 35200, 17200, -210, -1.7),
    ("028260", "삼성물산", "Samsung C&T", "Industrials", "Construction & engineering", 154000, 216520, 25800, 65000, 41500, 1710, 0.9),
]


def demo_snapshot():
    entries = []
    for ticker, name_ko, name_en, sector, industry, price, volume, cap_bn, assets_bn, equity_bn, income_bn, pct in ROWS:
        pe = round(cap_bn / income_bn, 2) if income_bn > 0 else None
        pb = round(cap_bn / equity_bn, 2) if equity_bn > 0 else None
        entries.append({
            "ticker": ticker, "name": name_ko, "name_en": name_en,
            "sector": sector, "industry": industry, "industry_code": None,
            "price": price, "volume": volume, "market_cap_bn": cap_bn,
            "market_cap_krw": int(cap_bn * 1_000_000_000), "assets_bn": assets_bn,
            "equity_bn": equity_bn, "earnings_bn": income_bn, "pe": pe,
            "pb": pb, "change_pct": pct, "price_date": "2026-11-06",
            "report_period": "2026 H1", "report_date": "2026-06-30",
            "earnings_period": "LTM to 2026 H1 (FY2025 + 2026 H1 - 2025 H1)",
            "earnings_basis": "LTM", "statement_basis": "Consolidated",
            "dart_receipt": None,
            "naver_url": f"https://finance.naver.com/item/main.naver?code={ticker}",
        })
    return {
        "mode": "demo", "notice": "ILLUSTRATIVE DATA ONLY: prices, financials, multiples, and volumes are synthetic, not market observations.",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "price_date": "2026-11-06", "asset_threshold_bn": 200,
        "total_krx_stocks": None, "missing_financials": None,
        "companies": entries,
    }
