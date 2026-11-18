import pathlib
import unittest

from soccer_predictor.quiniela_sources import football_data, injuries, news

FIX = pathlib.Path(__file__).parent / "fixtures"


class TestSources(unittest.TestCase):
    def test_team_form_last_five_and_xg(self):
        rows = football_data.parse_csv(
            (FIX / "sp1_2627.csv").read_text(encoding="utf-8-sig")
        )
        f = football_data.team_form(rows, "Sevilla", n=5)
        self.assertEqual(len(f["matches"]), 5)
        self.assertEqual(len(f["recent"]), 5)
        self.assertTrue(set(f["recent"]) <= set("WDL"))
        self.assertGreaterEqual(f["xg"], 0)

    def test_closing_odds_normalized(self):
        rows = football_data.parse_csv(
            (FIX / "sp1_2627.csv").read_text(encoding="utf-8-sig")
        )
        odds = football_data.closing_odds(rows, "Sevilla", "Real Betis")
        if odds is not None:
            self.assertAlmostEqual(sum(odds.values()), 100.0, places=0)

    def test_injuries_parse(self):
        html = (FIX / "transfermarkt_injuries.html").read_text(
            encoding="utf-8", errors="ignore"
        )
        r = injuries.parse_injuries_html(html)
        self.assertGreaterEqual(len(r), 1)
        self.assertIn("name", r[0])
        self.assertIn("issue", r[0])
        self.assertTrue(all(p["name"] for p in r))
        self.assertEqual(len({p["name"] for p in r}), len(r))

    def test_injuries_skip_women(self):
        r = injuries.fetch_injuries("Eibar", women=True)
        self.assertFalse(r["ok"])
        self.assertEqual(r["count"], 0)

    def test_news_parse(self):
        xml = (FIX / "gnews_sevilla_betis.xml").read_text(
            encoding="utf-8", errors="ignore"
        )
        items = news.parse_rss(xml, limit=3)
        self.assertEqual(len(items), 3)
        self.assertTrue(items[0]["title"])

    def test_adapters_never_raise(self):
        def boom(*a, **k):
            raise RuntimeError("sin red")

        original = football_data._get_text
        football_data._get_text = boom
        try:
            r = football_data.load_league("SP1")
            self.assertFalse(r["ok"])
            self.assertEqual(r["rows"], [])
        finally:
            football_data._get_text = original

        original = injuries._get_text
        injuries._get_text = boom
        try:
            r = injuries.fetch_injuries("Sevilla")
            self.assertFalse(r["ok"])
            self.assertEqual(r["count"], 0)
        finally:
            injuries._get_text = original


if __name__ == "__main__":
    unittest.main()
