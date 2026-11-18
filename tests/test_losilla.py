import pathlib
import unittest

from soccer_predictor.quiniela_sources import losilla

FIX = pathlib.Path(__file__).parent / "fixtures"


class TestLosilla(unittest.TestCase):
    def setUp(self):
        self.csv = (FIX / "jornada23.csv").read_text(encoding="utf-8")
        self.html = (FIX / "jornada23_home.html").read_text(encoding="utf-8")

    def test_parse_csv_sections_and_values(self):
        sec = losilla.parse_csv(self.csv)
        self.assertEqual(set(sec), {"tecnicos", "quinielista", "lae", "real"})
        m1 = sec["real"][0]
        self.assertEqual(m1["n"], 1)
        self.assertEqual(m1["percentages"]["1"], 43.0)
        self.assertEqual(m1["percentages"]["X"], 29.0)
        self.assertEqual(m1["percentages"]["2"], 28.0)
        self.assertEqual(sec["quinielista"][0]["percentages"]["1"], 46.0)
        self.assertIsNone(sec["lae"][0]["lae"])

    def test_pleno_two_rows_and_four_columns(self):
        sec = losilla.parse_csv(self.csv)
        p = sec["real"][14]["pleno"]
        self.assertEqual(p["home"], {"0": 29.0, "1": 36.0, "2": 22.0, "M": 13.0})
        self.assertEqual(p["away"], {"0": 23.0, "1": 34.0, "2": 25.0, "M": 18.0})

    def test_parse_boleto_schedule_and_flags(self):
        b = losilla.parse_boleto(self.html)
        self.assertEqual(b["jornada"], 23)
        self.assertEqual(len(b["matches"]), 15)
        self.assertEqual(b["matches"][0]["day"], "SAB")
        self.assertEqual(b["matches"][0]["hour"], "14:00")
        self.assertFalse(b["matches"][0]["is_women"])
        self.assertTrue(b["matches"][10]["is_women"])
        self.assertTrue(b["matches"][14]["is_pleno"])

    def test_fetch_merges_and_falls_back_to_real(self):
        def fake_get(url, params=None, timeout=20):
            return self.csv if "analisisSigno" in url else self.html

        original = losilla._get_text
        losilla._get_text = fake_get
        try:
            j = losilla.fetch_jornada(jornada=23)
        finally:
            losilla._get_text = original
        self.assertEqual(j["jornada"], 23)
        self.assertEqual(j["matches"][0]["home"], "Alaves")
        self.assertEqual(j["matches"][0]["percentages"]["probables"]["1"], 43.0)
        self.assertIsNone(j["matches"][0]["lae"])
        self.assertTrue(j["matches"][10]["is_women"])

    def test_pleno_match_has_no_1x2_percentages(self):
        def fake_get(url, params=None, timeout=20):
            return self.csv if "analisisSigno" in url else self.html

        original = losilla._get_text
        losilla._get_text = fake_get
        try:
            j = losilla.fetch_jornada(jornada=23)
        finally:
            losilla._get_text = original
        pleno = j["matches"][14]
        self.assertIsNone(pleno["probables"])
        self.assertIsNone(pleno["lae"])
        self.assertIsNotNone(pleno["pleno"])
        self.assertEqual(pleno["pleno"]["home"]["M"], 13.0)

    def test_close_keeps_the_hour(self):
        b = losilla.parse_boleto(self.html)
        self.assertIn("21/11", b["close"])
        self.assertIn("12:30", b["close"])

    def test_fetch_works_offline_with_saved_html(self):
        def boom(*args, **kwargs):
            raise RuntimeError("sin red")

        original = losilla._get_text
        losilla._get_text = boom
        try:
            j = losilla.fetch_jornada(jornada=23, html=self.html)
        finally:
            losilla._get_text = original
        self.assertEqual(len(j["matches"]), 15)
        self.assertIsNone(j["matches"][0]["probables"])
        self.assertEqual(j["matches"][0]["home"], "Alaves")

    def test_old_cache_without_close_hour_is_refreshed(self):
        import tempfile

        from soccer_predictor.quiniela_sources.cache import Cache

        def fake_get(url, params=None, timeout=20):
            return self.csv if "analisisSigno" in url else self.html

        with tempfile.TemporaryDirectory() as d:
            cache = Cache(pathlib.Path(d))
            cache.set(f"losilla_23_{losilla._season_number()}",
                      {"jornada": 23, "close": "SÁBADO 21/11", "matches": []})
            original = losilla._get_text
            losilla._get_text = fake_get
            try:
                j = losilla.fetch_jornada(jornada=23, cache=cache)
            finally:
                losilla._get_text = original
        self.assertIn(":", j["close"])

    def test_cache_roundtrip(self):
        import tempfile

        from soccer_predictor.quiniela_sources.cache import Cache

        with tempfile.TemporaryDirectory() as d:
            c = Cache(pathlib.Path(d), max_age_hours=6)
            self.assertIsNone(c.get("x"))
            c.set("x", {"a": 1})
            self.assertEqual(c.get("x"), {"a": 1})
