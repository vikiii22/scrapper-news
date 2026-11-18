import pathlib
import tempfile
import unittest
from datetime import datetime

from soccer_predictor import jornada


def fake_predict(home, away, comp="", **kw):
    return {"prob_1x2": {"home": 0.5, "draw": 0.3, "away": 0.2},
            "prediction_1x2": "1", "expected_goals": {"home": 1.6, "away": 1.0},
            "positions": {"home": 5, "away": 10}, "low_confidence": False,
            "data_sources": {"home": "fake", "away": "fake",
                             "home_recent": "WWDLW", "away_recent": "LDLWW"}}


class TestJornada(unittest.TestCase):
    def _entry(self):
        base = {"home": "Alaves", "away": "Deportivo", "is_women": False,
                "is_pleno": False,
                "percentages": {"jugados": {"1": 47, "X": 36, "2": 17},
                                "lae": None,
                                "probables": {"1": 43, "X": 29, "2": 28},
                                "tecnicos": {"1": 44, "X": 30, "2": 26}},
                "lae": None, "probables": {"1": 43, "X": 29, "2": 28},
                "pleno": None}
        ms = [dict(base, n=i) for i in range(1, 15)]
        ms.append(dict(base, n=15, is_pleno=True,
                       pleno={"home": {"0": 29, "1": 36, "2": 22, "M": 13},
                              "away": {"0": 23, "1": 34, "2": 25, "M": 18}}))
        return {"jornada": 23, "season": 2027, "close": "SAB 21/11 12:30",
                "sources": {}, "matches": ms}

    def test_is_closed_uses_the_close_hour(self):
        self.assertFalse(jornada._is_closed(
            "SÁBADO 21/11 12:30", datetime(2026, 11, 21, 12, 29)))
        self.assertTrue(jornada._is_closed(
            "SÁBADO 21/11 12:30", datetime(2026, 11, 21, 12, 31)))
        self.assertFalse(jornada._is_closed(
            "SÁBADO 21/11 21:00", datetime(2026, 11, 21, 20, 59)))
        self.assertTrue(jornada._is_closed(
            "SÁBADO 21/11 21:00", datetime(2026, 11, 21, 21, 1)))
        self.assertIsNone(jornada._is_closed("", datetime(2026, 11, 21, 12, 0)))

    def test_unknown_close_requires_force(self):
        entry = self._entry()
        entry["close"] = ""
        original = jornada.fetch_jornada
        jornada.fetch_jornada = lambda **k: entry
        try:
            out = jornada.run(jornada=23, predict_fn=fake_predict)
        finally:
            jornada.fetch_jornada = original
        self.assertEqual(out.get("error"), "cierre_desconocido")

    def test_forced_run_marks_the_report(self):
        entry = self._entry()
        entry["close"] = "SAB 01/11 12:30"
        original = jornada.fetch_jornada
        original_contexts = jornada.build_contexts
        original_understat = jornada.understat.league_xg
        original_markets = jornada.markets.outright_context
        jornada.fetch_jornada = lambda **k: entry
        jornada.build_contexts = lambda *a, **k: {}
        jornada.understat.league_xg = lambda *a, **k: {"ok": False, "error": "n/d"}
        jornada.markets.outright_context = lambda *a, **k: {"ok": False, "error": "n/d"}
        try:
            with tempfile.TemporaryDirectory() as d:
                out = jornada.run(jornada=23, force=True,
                                  predict_fn=fake_predict,
                                  output_dir=pathlib.Path(d))
                md = pathlib.Path(out["report_paths"]["markdown"]).read_text(
                    encoding="utf-8")
        finally:
            jornada.fetch_jornada = original
            jornada.build_contexts = original_contexts
            jornada.understat.league_xg = original_understat
            jornada.markets.outright_context = original_markets
        self.assertTrue(out.get("forced"))
        self.assertIn("FORZADO", md)

    def test_main_returns_one_on_unexpected_error(self):
        original = jornada.run

        def boom(**kwargs):
            raise RuntimeError("Losilla caído")

        jornada.run = boom
        try:
            code = jornada.main([])
        finally:
            jornada.run = original
        self.assertEqual(code, 1)

    def test_women_skips_masculine_elo_and_uses_female_news_query(self):
        original = (jornada.espn.search_team, jornada.injuries.fetch_injuries,
                    jornada.news.headlines, jornada.clubelo.elo)
        seen = {}

        def fake_news(query, **kwargs):
            seen["query"] = query
            return {"ok": False, "items": [], "error": "n/d"}

        jornada.espn.search_team = lambda *a, **k: ("esp.w.1", "1", "Eibar")
        jornada.injuries.fetch_injuries = lambda *a, **k: {
            "ok": False, "players": [], "count": 0}
        jornada.news.headlines = fake_news
        jornada.clubelo.elo = lambda *a, **k: {"ok": True, "elo": 1500}
        try:
            _, context = jornada._context_for(
                {"n": 11, "home": "Eibar", "away": "Atletico Madrid",
                 "is_women": True}, {}, None)
        finally:
            (jornada.espn.search_team, jornada.injuries.fetch_injuries,
             jornada.news.headlines, jornada.clubelo.elo) = original
        self.assertEqual(context["elo"], {"home": None, "away": None})
        self.assertIn("femenino", seen["query"])

    def test_analyze_forwards_persist_false(self):
        seen = {}

        def capturing_predict(home, away, comp="", **kwargs):
            seen.update(kwargs)
            return {"prob_1x2": {"home": 0.5, "draw": 0.3, "away": 0.2},
                    "prediction_1x2": "1",
                    "expected_goals": {"home": 1.6, "away": 1.0},
                    "data_sources": {"home_recent": "WWDLW",
                                     "away_recent": "LDLWW"}}

        jornada.analyze_matches(self._entry(), predict_fn=capturing_predict)
        self.assertFalse(seen["persist"])

    def test_uses_probables_when_lae_missing(self):
        e = jornada.analyze_matches(self._entry(), predict_fn=fake_predict)
        m = e["matches"][0]
        self.assertEqual(m["modelo"], {"1": 50.0, "X": 30.0, "2": 20.0})
        self.assertAlmostEqual(m["valor"]["2"], -8.0, places=1)
        self.assertIsNone(m["lae"])

    def test_missing_injury_data_is_none(self):
        entry = self._entry()
        entry["matches"][0]["is_women"] = True
        contexts = {1: {"injuries": {"home": {"ok": False, "count": 0},
                                     "away": {"ok": False, "count": 0}}}}
        out = jornada.analyze_matches(entry, predict_fn=fake_predict,
                                      contexts=contexts)
        self.assertIsNone(out["matches"][0]["absences"]["home"])
        self.assertIsNone(out["matches"][0]["absences"]["away"])

    def test_competition_detection(self):
        self.assertEqual(jornada.competition_for({"is_women": True}, {}), "Liga F")
        self.assertEqual(jornada.competition_for({}, {"league": "esp.2"}), "Segunda División")
        self.assertEqual(jornada.competition_for({}, {"league": "esp.1"}), "La Liga")

    def test_run_writes_report_and_boletos(self):
        e = self._entry()
        original = jornada.fetch_jornada
        original_contexts = jornada.build_contexts
        jornada.fetch_jornada = lambda **k: e
        jornada.build_contexts = lambda *a, **k: {}
        try:
            with tempfile.TemporaryDirectory() as d:
                out = jornada.run(jornada=23, force=True,
                                  predict_fn=fake_predict,
                                  output_dir=pathlib.Path(d))
        finally:
            jornada.fetch_jornada = original
            jornada.build_contexts = original_contexts
        self.assertEqual(out["jornada"], 23)
        self.assertIn("boleto_rentable", out)
        self.assertIn("boleto_conservador", out)
        self.assertEqual(len(out["boleto_rentable"]["columns"]), 24)

    def test_main_aborts_when_not_playable(self):
        e = self._entry()
        e["played"] = True
        original = jornada.fetch_jornada
        jornada.fetch_jornada = lambda **k: e
        try:
            code = jornada.main(["--jornada", "23"])
        finally:
            jornada.fetch_jornada = original
        self.assertNotEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
