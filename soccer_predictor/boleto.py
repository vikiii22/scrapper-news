"""Boletos de quiniela: selección de signos y reducción de 24 apuestas.

La reducción se genera como un código de cobertura sobre las combinaciones
posibles de los 6 partidos múltiples (3 dobles + 3 triples): 24 columnas que
garantizan 13 aciertos si los 8 fijos entran, y 14 cuando la combinación real
está entre las 24 (24/216 = 11,1 %).
"""

from __future__ import annotations

import itertools
import math
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    from .prediction_engine import poisson_pmf
    from .quiniela import pleno_suggestion
except ImportError:  # pragma: no cover
    from prediction_engine import poisson_pmf
    from quiniela import pleno_suggestion

SIGNS = ("1", "X", "2")
PLENO_LABELS = ("0", "1", "2", "M")
PLENO_VALUES = (0, 1, 2, 3)
BETS = 24
COST_PER_BET = 0.75


def _distance(a: Iterable[int], b: Iterable[int]) -> int:
    return sum(x != y for x, y in zip(a, b))


def covering_code(sizes: List[int]) -> List[Tuple[int, ...]]:
    """Código greedy determinista con radio 1 sobre el producto de tamaños."""
    universe = list(itertools.product(*[range(size) for size in sizes]))
    covered: set = set()
    code: List[Tuple[int, ...]] = []

    while len(covered) < len(universe):
        best = None
        best_gain = 0
        for point in universe:
            gain = sum(
                1 for candidate in universe
                if candidate not in covered and _distance(candidate, point) <= 1
            )
            if gain > best_gain:
                best_gain = gain
                best = point
        if best is None or best_gain == 0:
            break
        code.append(best)
        covered.update(
            candidate for candidate in universe if _distance(candidate, best) <= 1
        )

    if len(code) != BETS:
        raise ValueError(f"la reducción generó {len(code)} columnas, no {BETS}")
    return code


def _entropy(probs: Dict[str, float]) -> float:
    return -sum(p * math.log(p) for p in probs.values() if p > 0)


def _canonical(signs: Iterable[str]) -> List[str]:
    chosen = set(signs)
    return [sign for sign in SIGNS if sign in chosen]


def _model_probs(match: Dict[str, Any]) -> Dict[str, float]:
    model = match.get("modelo") or {}
    return {sign: max(0.0, float(model.get(sign, 0) or 0)) / 100.0 for sign in SIGNS}


def _reference(match: Dict[str, Any]) -> Dict[str, float]:
    percentages = match.get("percentages") or {}
    ref = percentages.get("lae") or percentages.get("probables") or {}
    parsed = {sign: float(ref.get(sign, 0) or 0) for sign in SIGNS}
    if sum(parsed.values()) <= 0:
        return {sign: 100.0 / 3 for sign in SIGNS}
    return parsed


def _double_signs(probs: Dict[str, float]) -> List[str]:
    ordered = sorted(SIGNS, key=lambda sign: probs.get(sign, 0.0), reverse=True)
    if ordered[1] == "X":
        return _canonical([ordered[0], "X"])
    return ["1", "2"]


def _top_pct(table: Dict[str, float]) -> float:
    return max(table.values()) if table else 0.0


def _swap_fragile_fixed(signs: Dict[int, List[str]],
                        model: Dict[int, Dict[str, float]],
                        market: Dict[int, Dict[str, float]]) -> Dict[int, List[str]]:
    """No fijar un favorito local que el mercado no respalda.

    Si un fijo tiene mercado < 50 % y el modelo lo infla más de 8 puntos, se
    convierte en doble (con el patrón del mercado) y se fija el doble más
    fiable del mercado (≥ 55 % y brecha ≤ 10). Así no se rompe el 3+3.
    """
    fixed = [n for n, value in signs.items() if len(value) == 1]
    doubles = [n for n, value in signs.items() if len(value) == 2]
    fragile = [
        n for n in fixed
        if _top_pct(market.get(n, {})) < 50
        and _top_pct(model.get(n, {})) - _top_pct(market.get(n, {})) > 8
    ]
    reliable = [
        n for n in doubles
        if _top_pct(market.get(n, {})) >= 55
        and abs(_top_pct(model.get(n, {})) - _top_pct(market.get(n, {}))) <= 10
    ]
    if not fragile or not reliable:
        return signs

    fragile_match = max(
        fragile, key=lambda n: _top_pct(model[n]) - _top_pct(market[n])
    )
    reliable_match = max(reliable, key=lambda n: _top_pct(market[n]))
    signs[fragile_match] = _double_signs(market[fragile_match])
    signs[reliable_match] = [
        max(SIGNS, key=lambda sign: market[reliable_match].get(sign, 0.0))
    ]
    return signs


def select_signs(matches: List[Dict[str, Any]],
                 profile: str = "rentable") -> Dict[int, List[str]]:
    """3 triples, 3 dobles y 8 fijos. Determinista para la misma entrada."""
    if profile not in ("rentable", "seguro"):
        raise ValueError("profile debe ser 'rentable' o 'seguro'")

    pool = [m for m in matches if m.get("n") != 15]
    probs = {m["n"]: _model_probs(m) for m in pool}
    refs = {m["n"]: _reference(m) for m in pool}
    conf = {n: max(p.values()) for n, p in probs.items()}
    xprob = {n: p.get("X", 0.0) for n, p in probs.items()}
    entropy = {n: _entropy(p) for n, p in probs.items()}
    value = {
        n: max([float(v or 0) for v in (m.get("valor") or {}).values()] or [0.0])
        for n, m in ((m["n"], m) for m in pool)
    }

    # El partido más fiable nunca se dobla ni se triplica.
    safest = max(conf, key=lambda n: (conf[n], -n))

    def openness(n: int) -> float:
        return (1 - conf[n]) + 0.5 * xprob[n] + 0.01 * max(0.0, value[n])

    def uncertainty(n: int) -> float:
        return xprob[n] + 0.35 * entropy[n] + 0.01 * max(0.0, value[n])

    remaining = [n for n in conf if n != safest]
    if profile == "seguro":
        # El boleto conservador dobla los partidos con más riesgo de X y
        # reserva los triples para los siguientes más abiertos.
        by_draw = sorted(remaining, key=lambda n: (xprob[n], -n), reverse=True)
        doubles = by_draw[:3]
        triples = sorted(
            [n for n in remaining if n not in doubles],
            key=lambda n: (xprob[n], -n), reverse=True,
        )[:3]
    else:
        triples = sorted(remaining, key=lambda n: (uncertainty(n), -n),
                         reverse=True)[:3]
        doubles = sorted(
            [n for n in remaining if n not in triples],
            key=lambda n: (openness(n), -n), reverse=True,
        )[:3]

    signs: Dict[int, List[str]] = {}
    for n in sorted(conf):
        if n in triples:
            signs[n] = ["1", "X", "2"]
        elif n in doubles:
            signs[n] = _double_signs(probs[n] if profile == "rentable" else refs[n])
        else:
            table = probs[n] if profile == "rentable" else refs[n]
            signs[n] = [max(SIGNS, key=lambda sign: table.get(sign, 0.0))]
    model_pct = {
        n: {sign: probs[n].get(sign, 0.0) * 100 for sign in SIGNS}
        for n in probs
    }
    return _swap_fragile_fixed(signs, model_pct, refs)


def pleno_variants(lam_home: float, lam_away: float) -> Dict[str, Dict[str, str]]:
    seguro = pleno_suggestion(lam_home, lam_away)

    best = None
    best_prob = -1.0
    for h_label, h_value in zip(PLENO_LABELS, PLENO_VALUES):
        for a_label, a_value in zip(PLENO_LABELS, PLENO_VALUES):
            if h_value + a_value < 3:
                continue
            ph = poisson_pmf(lam_home, h_value) if h_value < 3 else \
                max(0.0, 1.0 - sum(poisson_pmf(lam_home, k) for k in range(3)))
            pa = poisson_pmf(lam_away, a_value) if a_value < 3 else \
                max(0.0, 1.0 - sum(poisson_pmf(lam_away, k) for k in range(3)))
            probability = ph * pa
            if probability > best_prob:
                best_prob = probability
                best = {"home": h_label, "away": a_label}

    return {"seguro": seguro, "bota": best or {"home": "2", "away": "1"}}


def build_boleto(matches: List[Dict[str, Any]],
                 profile: str = "rentable") -> Dict[str, Any]:
    signs = select_signs(matches, profile)
    multiples = {n: signs[n] for n in sorted(signs) if len(signs[n]) > 1}
    # Orden canónico por tamaño: el código greedy da 24 para [2,2,2,3,3,3].
    multiple_numbers = sorted(multiples, key=lambda n: (len(multiples[n]), n))
    multiples = {n: multiples[n] for n in multiple_numbers}
    sizes = [len(value) for value in multiples.values()]
    code = covering_code(sizes)

    columns: List[List[str]] = []
    position = {n: index for index, n in enumerate(multiple_numbers)}
    for combination in code:
        column: List[str] = []
        for n in sorted(signs):
            if n in multiples:
                column.append(multiples[n][combination[position[n]]])
            else:
                column.append(signs[n][0])
        columns.append(column)

    pleno = {"home": "1", "away": "1"}
    pleno_match = next((m for m in matches if m.get("n") == 15), None)
    goals = (pleno_match or {}).get("expected_goals")
    if goals and goals.get("home") is not None and goals.get("away") is not None:
        pleno = pleno_suggestion(float(goals["home"]), float(goals["away"]))

    name = "Boleto rentable" if profile == "rentable" else "Boleto conservador"
    return {
        "name": name,
        "profile": profile,
        "bets": BETS,
        "cost_eur": BETS * COST_PER_BET,
        "signs": signs,
        "multiples": {
            "triples": [n for n in multiple_numbers if len(multiples[n]) == 3],
            "dobles": [n for n in multiple_numbers if len(multiples[n]) == 2],
        },
        "columns": columns,
        "pleno": pleno,
        "guarantee": {
            "text": ("13 si los 8 fijos entran y los dobles contienen el signo real; "
                     "14 si además la combinación exacta está entre las 24"),
            "p14": round(BETS / (2 ** 3 * 3 ** 3) * 100, 1),
            "bets": BETS,
            "fixed": 8,
        },
    }
