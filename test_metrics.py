import unittest
from app.metrics import calculate_financials, extract_statement, number, valuation, period_end
from app.industry import classify
from app.demo import demo_snapshot


def row(sj, account, amount, *, fs="CFS", code="", add=None):
    return {"sj_div": sj, "fs_div": fs, "account_id": code,
            "account_nm": account, "thstrm_amount": str(amount),
            "thstrm_add_amount": str(add) if add is not None else None,
            "thstrm_dt": "2026.01.01 ~ 2026.06.30"}


class MetricsTests(unittest.TestCase):
    def test_number(self):
        self.assertEqual(number("(1,234)"), -1234)
        self.assertEqual(number("-"), None)
        self.assertEqual(number("23,300"), 23300)

    def test_financial_statement_owner_and_ytd(self):
        data = [
            row("BS", "자산총계", "300,000", code="ifrs-full_Assets"),
            row("BS", "자본총계", 100000, code="ifrs-full_Equity"),
            row("BS", "지배기업소유주지분", 89000, code="ifrs-full_EquityAttributableToOwnersOfParent"),
            row("IS", "당기순이익", 90, add=150, code="ifrs-full_ProfitLoss"),
            row("IS", "지배기업 소유주 순이익", 70, add=125, code="ifrs-full_ProfitLossAttributableToOwnersOfParent"),
        ]
        st = extract_statement(data, 2026, "11012")
        self.assertEqual(st["assets"], 300000)
        self.assertEqual(st["equity_parent"], 89000)
        self.assertEqual(st["net_income_parent_ytd"], 125)
        self.assertEqual(st["as_of"], "2026-06-30")

    def test_no_misleading_nci_fallback(self):
        rows = [row("BS","자산총계",300000,code="ifrs-full_Assets"),
                row("BS","자본총계",100000,code="ifrs-full_Equity"),
                row("IS","당기순이익",1000,add=1200,code="ifrs-full_ProfitLoss")]
        st = extract_statement(rows, 2026, "11012")
        self.assertIsNone(st["equity_parent"])
        self.assertIsNone(st["net_income_parent_ytd"])

    def test_ltm(self):
        base = {"basis": "Consolidated", "assets": 301_000, "equity_parent": 200_000,
                "as_of": "2026-06-30", "receipt_no": "12345"}
        d = {
            (2026,"11012"): {**base,"year":2026,"code":"11012","label":"2026 H1","net_income_parent_ytd":9000},
            (2025,"11011"): {**base,"year":2025,"code":"11011","label":"2025 FY","net_income_parent_ytd":16000},
            (2025,"11012"): {**base,"year":2025,"code":"11012","label":"2025 H1","net_income_parent_ytd":5000},
        }
        f = calculate_financials(d, 2026)
        self.assertEqual(f["earnings_krw"], 20000)
        self.assertEqual(f["earnings_basis"], "LTM")
        self.assertEqual(f["report_period"], "2026 H1")
        self.assertEqual(valuation(100_000, f), (5, 0.5))

    def test_fy_fallback_and_negative_earnings(self):
        d={(2025,"11011"): {"year":2025,"code":"11011","label":"2025 FY", "basis":"Separate (no CFS)", "assets":900, "equity_parent":200,
             "net_income_parent_ytd":-50,"receipt_no":None,"as_of":"2025-12-31"}}
        f=calculate_financials(d,2026)
        self.assertEqual(f["earnings_basis"],"FY")
        self.assertEqual(valuation(800,f),(None,4.0))

    def test_missing_prior_ytd_is_not_ltm(self):
        d={(2026,"11012"):{"year":2026,"code":"11012","label":"2026 H1","basis":"Consolidated","assets":300,"equity_parent":150,"net_income_parent_ytd":30,"as_of":"2026-06-30"},
           (2025,"11011"):{"year":2025,"code":"11011","label":"2025 FY","basis":"Consolidated","assets":280,"equity_parent":150,"net_income_parent_ytd":50,"as_of":"2025-12-31"}}
        f=calculate_financials(d,2026)
        self.assertIsNone(f["earnings_krw"])
        self.assertIsNone(f["earnings_basis"])

    def test_sector_and_demo(self):
        self.assertEqual(classify("26110")[0], "Information Technology")
        d=demo_snapshot()
        self.assertEqual(d["mode"],"demo")
        self.assertGreater(len(d["companies"]), 10)
        self.assertTrue(all(x["assets_bn"] > 200 for x in d["companies"]))


if __name__ == "__main__": unittest.main()
