import itertools
import json
import pathlib
import unittest

from soccer_predictor import boleto

FIX = pathlib.Path(__file__).parent / "fixtures"


def _entry(n=1, p1=50, px=25, p2=25, prob=None, modelo=None):
    return {"n": n, "modelo": modelo or {"1": p1, "X": px, "2": p2},
            "valor": {"1": 0, "X": 0, "2": 0},
            "percentages": {"probables": prob or {"1": p1, "X": px, "2": p2}},
            "pleno": None}


MATCHES = [(60, 20, 20), (40, 30, 30), (50, 30, 20), (30, 40, 30),
           (70, 15, 15), (45, 25, 30), (35, 35, 30), (55, 25, 20),
           (40, 35, 25), (65, 20, 15), (20, 30, 50), (80, 12, 8),
           (50, 25, 25), (45, 30, 25)]


def _matches():
    return [_entry(i, *MATCHES[i - 1]) for i in range(1, 15)]


class TestCovering(unittest.TestCase):
    def test_24_columns_cover_all_216_with_radius_one(self):
        pts = list(itertools.product(*[range(s) for s in (2, 2, 2, 3, 3, 3)]))
        code = boleto.covering_code([2, 2, 2, 3, 3, 3])
        self.assertEqual(len(code), 24)
        self.assertEqual(len(set(code)), 24)
        for p in pts:
            self.assertTrue(
                any(sum(a != b for a, b in zip(p, c)) <= 1 for c in code)
            )

    def test_signs_shape_and_determinism(self):
        s = boleto.select_signs(_matches(), "rentable")
        self.assertEqual(len(s), 14)
        self.assertEqual(sum(1 for v in s.values() if len(v) == 3), 3)
        self.assertEqual(sum(1 for v in s.values() if len(v) == 2), 3)
        self.assertEqual(sum(1 for v in s.values() if len(v) == 1), 8)
        self.assertEqual(s, boleto.select_signs(_matches(), "rentable"))

    def test_boleto_cost_columns_and_guarantee(self):
        b = boleto.build_boleto(_matches(), "rentable")
        self.assertEqual(b["bets"], 24)
        self.assertEqual(b["cost_eur"], 18.0)
        self.assertEqual(len(b["columns"]), 24)
        self.assertTrue(all(len(c) == 14 for c in b["columns"]))
        self.assertIn("13", b["guarantee"]["text"])
        self.assertAlmostEqual(b["guarantee"]["p14"], 11.1, places=1)

    def test_profiles_differ(self):
        b1 = boleto.build_boleto(_matches(), "rentable")
        b2 = boleto.build_boleto(_matches(), "seguro")
        self.assertNotEqual(b1["signs"], b2["signs"])

    def test_columns_are_unique_and_use_selected_signs(self):
        b = boleto.build_boleto(_matches(), "rentable")
        self.assertEqual(len({tuple(c) for c in b["columns"]}), 24)
        numbers = sorted(b["signs"])
        for column in b["columns"]:
            self.assertEqual(len(column), 14)
            for n, sign in zip(numbers, column):
                self.assertIn(sign, b["signs"][n])

    def test_expanded_columns_keep_the_covering_guarantee(self):
        b = boleto.build_boleto(_matches(), "rentable")
        numbers = sorted(b["signs"])
        multiple = [n for n in numbers if len(b["signs"][n]) > 1]
        position = {n: index for index, n in enumerate(multiple)}
        tuples = []
        for column in b["columns"]:
            tuples.append(tuple(
                b["signs"][n].index(sign)
                for n, sign in zip(numbers, column) if n in position
            ))
        sizes = [len(b["signs"][n]) for n in multiple]
        universe = list(itertools.product(*[range(size) for size in sizes]))
        self.assertEqual(len(set(tuples)), 24)
        for point in universe:
            self.assertTrue(any(
                sum(a != c for a, c in zip(point, row)) <= 1 for row in tuples
            ))

    def test_swap_fragile_fixed_with_reliable_double(self):
        signs = {1: ["1"], 2: ["1"], 7: ["1", "2"]}
        model = {1: {"1": 80, "X": 12, "2": 8},
                 2: {"1": 60, "X": 23, "2": 17},
                 7: {"1": 50, "X": 25, "2": 25}}
        market = {1: {"1": 80, "X": 12, "2": 8},
                  2: {"1": 49, "X": 27, "2": 24},
                  7: {"1": 25, "X": 20, "2": 55}}
        out = boleto._swap_fragile_fixed(signs, model, market)
        self.assertEqual(out[2], ["1", "X"])
        self.assertEqual(out[7], ["2"])

    def test_j23_fragile_rayo_is_doubled_and_atleti_fixed(self):
        matches = json.loads((FIX / "j23_matches.json").read_text(encoding="utf-8"))
        rentable = boleto.select_signs(matches, "rentable")
        self.assertEqual(rentable[2], ["1", "X"])
        self.assertEqual(rentable[7], ["2"])
        self.assertEqual(rentable[1], ["1", "2"])
        self.assertEqual(rentable[5], ["1", "2"])
        self.assertEqual(len(rentable[8]), 3)
        self.assertEqual(len(rentable[11]), 3)
        self.assertEqual(len(rentable[12]), 3)

        seguro = boleto.select_signs(matches, "seguro")
        self.assertEqual(seguro[2], ["1", "X"])
        self.assertEqual(seguro[7], ["2"])
        self.assertEqual(seguro[1], ["1", "X"])
        self.assertEqual(seguro[8], ["1", "2"])

    def test_pleno_variants(self):
        p = boleto.pleno_variants(1.8, 1.1)
        self.assertIn(p["seguro"]["home"], "012M")
        self.assertIn(p["bota"]["away"], "012M")


if __name__ == "__main__":
    unittest.main()
