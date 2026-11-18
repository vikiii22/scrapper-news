import json
import pathlib
import tempfile
import unittest

from soccer_predictor import report

FIX = pathlib.Path(__file__).parent / "fixtures"


class TestReport(unittest.TestCase):
    def test_markdown_has_required_sections(self):
        e = json.loads((FIX / "entry_min.json").read_text(encoding="utf-8"))
        md = report.render_markdown(e)
        for s in ["JORNADA 23", "Boleto rentable", "Boleto conservador",
                  "Pleno al 15", "Garantía", "n/d", "Valor"]:
            self.assertIn(s, md)

    def test_write_report_creates_both_files(self):
        e = json.loads((FIX / "entry_min.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as d:
            md, js = report.write_report(e, pathlib.Path(d))
            self.assertTrue(md.exists() and js.exists())
            self.assertEqual(json.loads(js.read_text(encoding="utf-8"))["jornada"], 23)


if __name__ == "__main__":
    unittest.main()
