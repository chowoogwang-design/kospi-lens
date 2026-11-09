"""Broad, approximate sector groupings from DART/Korean KSIC industry codes.

KSIC is an activity classification, NOT GICS. We expose the raw 5-digit code.
"""
from __future__ import annotations

INDUSTRY_2 = {
    "01": ("Consumer Staples", "Agriculture"), "02": ("Materials", "Forestry"), "03": ("Consumer Staples", "Fishing"),
    "05": ("Energy", "Coal mining"), "06": ("Energy", "Oil & gas"), "07": ("Materials", "Metal mining"), "08": ("Materials", "Other mining"),
    "10": ("Consumer Staples", "Food products"), "11": ("Consumer Staples", "Beverages"), "12": ("Consumer Staples", "Tobacco"),
    "13": ("Consumer Discretionary", "Textiles"), "14": ("Consumer Discretionary", "Apparel"), "15": ("Consumer Discretionary", "Leather products"),
    "16": ("Materials", "Wood products"), "17": ("Materials", "Paper"), "18": ("Industrials", "Printing"),
    "19": ("Energy", "Petroleum & refining"), "20": ("Materials", "Chemicals"), "21": ("Health Care", "Pharmaceuticals & biotechnology"),
    "22": ("Materials", "Rubber & plastics"), "23": ("Materials", "Non-metallic minerals"), "24": ("Materials", "Primary metals"),
    "25": ("Industrials", "Fabricated metal products"), "26": ("Information Technology", "Electronics & semiconductors"),
    "27": ("Information Technology", "Precision & medical devices"), "28": ("Industrials", "Electrical equipment"),
    "29": ("Industrials", "Machinery & equipment"), "30": ("Consumer Discretionary", "Automobiles"),
    "31": ("Industrials", "Shipbuilding & transport equipment"), "32": ("Consumer Discretionary", "Furniture"),
    "33": ("Consumer Discretionary", "Other manufacturing"), "35": ("Utilities", "Electricity & utilities"),
    "36": ("Utilities", "Water utilities"), "38": ("Industrials", "Waste management"),
    "41": ("Industrials", "Construction & engineering"), "42": ("Industrials", "Civil engineering"),
    "46": ("Consumer Discretionary", "Wholesale trade"), "47": ("Consumer Discretionary", "Retail trade"),
    "49": ("Industrials", "Land transportation"), "50": ("Industrials", "Water transportation"),
    "51": ("Industrials", "Air transportation"), "52": ("Industrials", "Warehousing & logistics"),
    "55": ("Consumer Discretionary", "Hospitality"), "56": ("Consumer Discretionary", "Food services"),
    "58": ("Communication Services", "Publishing & gaming"), "59": ("Communication Services", "Film & media"),
    "60": ("Communication Services", "Broadcasting"), "61": ("Communication Services", "Telecommunications"),
    "62": ("Information Technology", "Software & IT services"), "63": ("Communication Services", "Information services"),
    "64": ("Financials", "Financial services"), "65": ("Financials", "Insurance"), "66": ("Financials", "Financial services"),
    "68": ("Real Estate", "Real estate"), "70": ("Industrials", "Management services"),
    "71": ("Industrials", "Professional services"), "72": ("Industrials", "Architecture & engineering"),
    "73": ("Information Technology", "Research & development"), "74": ("Industrials", "Other professional services"),
    "75": ("Industrials", "Business support services"), "85": ("Consumer Discretionary", "Education"),
    "86": ("Health Care", "Health care services"), "90": ("Communication Services", "Arts & entertainment"),
    "91": ("Consumer Discretionary", "Sports & leisure"),
}


def classify(code: str | None):
    digits = str(code or "").zfill(2)
    return INDUSTRY_2.get(digits[:2], ("Other / Unclassified", f"KSIC {code}" if code else "Not reported"))
