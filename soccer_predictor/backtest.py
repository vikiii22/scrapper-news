"""
Backtest: mide el acierto real del motor con temporadas ya jugadas.

Uso:
    python -m soccer_predictor.backtest --seasons 2024 2025 --league esp.1

Compara el motor actual (baseline) con el v2 (Dixon-Coles-lite) usando
únicamente datos ANTERIORES a cada partido (sin mirar al futuro).
Métricas: acierto 1X2, Brier y RPS (menor = mejor en ambas).
"""

from __future__ import annotations

import argparse
import math
from collections import defaultdict
from typing import Any, Dict, List, Tuple

from .scrapers import espn
from . import prediction_engine as pe


# ---------------------------------------------------------------------------
# Carga de partidos finalizados (ESPN, temporadas completas)
# ---------------------------------------------------------------------------

def load_season(league: str, season: int) -> List[Dict[str, Any]]:
    """[(date, home, away, hs, as)] ordenados por fecha."""
    out: List[Dict[str, Any]] = []
    for entry in espn._league_teams(league):
        tid = str(entry.get("team", {}).get("id"))
        data = espn._get(
            f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league}"
            f"/teams/{tid}/schedule", {"season": season})
        if not data:
            continue
        for ev in data.get("events") or []:
            comp = (ev.get("competitions") or [{}])[0]
            state = ((comp.get("status") or {}).get("type") or {})
            if not state.get("completed"):
                continue
            cs = comp.get("competitors") or []
            if len(cs) < 2:
                continue
            home = next((c for c in cs if c.get("homeAway") == "home"), cs[0])
            away = next((c for c in cs if c.get("homeAway") == "away"), cs[1])
            try:
                hs = int(float(home["score"]["value"]))
                as_ = int(float(away["score"]["value"]))
            except (KeyError, TypeError, ValueError):
                continue
            out.append({
                "date": (ev.get("date") or "")[:10],
                "home": home.get("team", {}).get("displayName", "?"),
                "away": away.get("team", {}).get("displayName", "?"),
                "hs": hs, "as": as_,
            })
    # deduplicar (cada partido aparece en el schedule de ambos equipos)
    seen, dedup = set(), []
    for m in sorted(out, key=lambda m: m["date"]):
        k = (m["date"], m["home"], m["away"])
        if k not in seen:
            seen.add(k)
            dedup.append(m)
    return dedup


# ---------------------------------------------------------------------------
# Baseline: réplica exacta de la fórmula actual del motor
# ---------------------------------------------------------------------------

def baseline_probs(gf_h: float, ga_h: float, rec_h: str,
                   gf_a: float, ga_a: float, rec_a: str,
                   home_edge: float = 0.35, away_pen: float = -0.20,
                   scale: float = 1.05,
                   h2h_tilt_h: float = 0.0, h2h_tilt_a: float = 0.0) -> Tuple[float, float, float]:
    import math as _m
    attack_h, defense_a = gf_h, ga_a
    attack_a, defense_h = gf_a, ga_h
    lam_h = _m.sqrt(max(attack_h, 0.01) * max(defense_a, 0.01)) * scale + home_edge + h2h_tilt_h
    lam_a = _m.sqrt(max(attack_a, 0.01) * max(defense_h, 0.01)) * scale + away_pen + h2h_tilt_a
    for f, d, sgn in ((rec_h, "h", 1), (rec_a, "a", 1)):
        bonus = sum(0.06 if r == "W" else (-0.06 if r == "L" else 0) for r in f) / max(len(f), 1)
        if d == "h":
            lam_h += bonus
        else:
            lam_a += bonus
    lam_h = round(max(0.3, min(3.5, lam_h)), 3)
    lam_a = round(max(0.3, min(3.5, lam_a)), 3)
    p = pe.match_probabilities(lam_h, lam_a)
    return p["home"], p["draw"], p["away"]


# ---------------------------------------------------------------------------
# v2: fuerzas ataque/defensa normalizadas + Dixon-Coles + decaimiento temporal
# ---------------------------------------------------------------------------

def dixon_coles(probs, lam_h: float, lam_a: float, rho: float):
    """Ajusta la matriz 0-0/1-0/0-1/1-1 por correlación de marcadores bajos."""
    m = probs.copy()
    def tau(x, y):
        if x == 0 and y == 0:
            return 1 - lam_h * lam_a * rho
        if x == 0 and y == 1:
            return 1 + lam_h * rho
        if x == 1 and y == 0:
            return 1 + lam_a * rho
        if x == 1 and y == 1:
            return 1 - rho
        return 1.0
    for x in range(2):
        for y in range(2):
            m[x, y] *= tau(x, y)
    return m / m.sum()


def v2_probs(hist_h: List[Tuple[int, int, bool]],
             hist_a: List[Tuple[int, int, bool]],
             league_avg_h: float, league_avg_a: float,
             rho: float = -0.12, decay: float = 0.12,
             shrink: float = 4.0, venue_split: bool = False,
             form_n: int = 6) -> Tuple[float, float, float]:
    """
    hist: [(goles_a_favor, goles_en_contra, fue_local)] más antiguo -> reciente.
    venue_split=True: el ataque local solo se estima con partidos en casa
    (y así con las 4 combinaciones). Es lo estándar en la literatura.
    """
    def weights(n):
        return [math.exp(-decay * (n - 1 - i)) for i in range(n)]

    def ratings(hist, want_home: bool):
        w = weights(len(hist))
        att = def_ = 0.0
        w_att = w_def = 0.0
        for (gf, ga, was_home), wi in zip(hist, w):
            if venue_split and was_home != want_home:
                continue
            denom_att = league_avg_h if was_home else league_avg_a
            denom_def = league_avg_a if was_home else league_avg_h
            att += (gf / denom_att) * wi
            w_att += wi
            def_ += (ga / denom_def) * wi
            w_def += wi
        if w_att == 0 or w_def == 0:  # sin muestra en esa sede -> neutro
            return 1.0, 1.0
        att = (att + shrink * 1.0) / (w_att + shrink)
        def_ = (def_ + shrink * 1.0) / (w_def + shrink)
        return att, def_

    ah, _ = ratings(hist_h, True)
    _, da = ratings(hist_a, False)
    # defensa local en casa y ataque visitante fuera:
    _, dh_home = ratings(hist_h, True)
    aa_away, _ = ratings(hist_a, False)
    lam_h = max(0.15, league_avg_h * ah * da)
    lam_a = max(0.15, league_avg_a * aa_away * dh_home)
    lam_h = min(3.8, lam_h)
    lam_a = min(3.8, lam_a)

    import numpy as np
    max_g = 8
    m = np.zeros((max_g + 1, max_g + 1))
    for i in range(max_g + 1):
        for j in range(max_g + 1):
            m[i, j] = pe.poisson_pmf(lam_h, i) * pe.poisson_pmf(lam_a, j)
    m = m / m.sum()
    m = dixon_coles(m, lam_h, lam_a, rho)
    hw = dw = aw = 0.0
    for i in range(max_g + 1):
        for j in range(max_g + 1):
            if i > j:
                hw += m[i, j]
            elif i == j:
                dw += m[i, j]
            else:
                aw += m[i, j]
    return hw, dw, aw


# ---------------------------------------------------------------------------
# Bucle de backtest
# ---------------------------------------------------------------------------

def run(matches: List[Dict], rho=-0.12, decay=0.12, shrink=4.0,
        form_n=6, venue_split=False, verbose=False,
        home_edge=0.35, away_pen=-0.20, scale=1.05, h2h_w=0.0) -> Dict[str, Any]:
    hist: Dict[str, List[Tuple[int, int, bool]]] = defaultdict(list)
    past: List[Dict] = []  # partidos ya jugados (para H2H sin mirar al futuro)
    res = {"n": 0, "base_acc": 0, "v2_acc": 0,
           "base_brier": 0.0, "v2_brier": 0.0,
           "base_rps": 0.0, "v2_rps": 0.0}
    for m in matches:
        hh, aa = hist[m["home"]], hist[m["away"]]
        if len(hh) < 3 or len(aa) < 3:
            _push(hist, m)
            past.append(m)
            continue
        hh_w, aa_w = hh[-form_n:], aa[-form_n:]

        def avg(h, idx):
            return sum(x[idx] for x in h) / len(h)

        rec_h = "".join("W" if gf > ga else ("D" if gf == ga else "L")
                        for gf, ga, _ in hh_w)
        rec_a = "".join("W" if gf > ga else ("D" if gf == ga else "L")
                        for gf, ga, _ in aa_w)
        # H2H pasado: + si el local domina el historial y viceversa
        tilt_h = tilt_a = 0.0
        if h2h_w:
            hw = aw = dr = 0
            for q in past:
                teams = {q["home"], q["away"]}
                if {m["home"], m["away"]} != teams:
                    continue
                # ganador desde la perspectiva del actual local/visitante
                if q["hs"] == q["as"]:
                    dr += 1
                else:
                    winner = q["home"] if q["hs"] > q["as"] else q["away"]
                    if winner == m["home"]:
                        hw += 1
                    else:
                        aw += 1
            g = hw + aw + dr
            if g:
                tilt_h = h2h_w * (hw - aw) / g
                tilt_a = h2h_w * (aw - hw) / g
        try:
            bp = baseline_probs(avg(hh_w, 0), avg(hh_w, 1), rec_h,
                                avg(aa_w, 0), avg(aa_w, 1), rec_a,
                                home_edge, away_pen, scale, tilt_h, tilt_a)
        except Exception:
            _push(hist, m)
            past.append(m)
            continue

        # medias de la liga hasta la fecha (temporada en curso)
        lg = [x for x in matches if x["date"] < m["date"]]
        if len(lg) < 10:
            _push(hist, m)
            continue
        avg_h = sum(x["hs"] for x in lg) / len(lg)
        avg_a = sum(x["as"] for x in lg) / len(lg)
        vp = v2_probs([(gf, ga, wl) for gf, ga, wl in hh_w],
                      [(gf, ga, wl) for gf, ga, wl in aa_w],
                      avg_h, avg_a, rho, decay, shrink, venue_split, form_n)

        actual = (1.0, 0.0, 0.0) if m["hs"] > m["as"] else (
            (0.0, 1.0, 0.0) if m["hs"] == m["as"] else (0.0, 0.0, 1.0))
        for key, p in (("base", bp), ("v2", vp)):
            pick = max(range(3), key=lambda i: p[i])
            if pick == actual.index(1.0):
                res[f"{key}_acc"] += 1
            res[f"{key}_brier"] += sum((p[i] - actual[i]) ** 2 for i in range(3)) / 3
            # RPS para 1X2 ordenado (1 > X > 2 no es ordinal puro; usamos Brier+RPS con orden local > empate > visita)
            cum_p, cum_a, rps = 0.0, 0.0, 0.0
            for i in range(2):
                cum_p += p[i]
                cum_a += actual[i]
                rps += (cum_p - cum_a) ** 2
            res[f"{key}_rps"] += rps / 2
        res["n"] += 1
        _push(hist, m)
        past.append(m)

    n = max(res["n"], 1)
    return {
        "n": res["n"],
        "base": {"acc": res["base_acc"] / n, "brier": res["base_brier"] / n,
                 "rps": res["base_rps"] / n},
        "v2": {"acc": res["v2_acc"] / n, "brier": res["v2_brier"] / n,
               "rps": res["v2_rps"] / n},
    }


def _push(hist, m):
    hist[m["home"]].append((m["hs"], m["as"], True))
    hist[m["away"]].append((m["as"], m["hs"], False))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seasons", nargs="+", type=int, default=[2024, 2025])
    ap.add_argument("--league", default="esp.1")
    ap.add_argument("--rho", type=float, default=-0.12)
    ap.add_argument("--decay", type=float, default=0.12)
    ap.add_argument("--shrink", type=float, default=4.0)
    ap.add_argument("--grid", action="store_true", help="barrido de hiperparámetros")
    ap.add_argument("--venue-split", action="store_true")
    ap.add_argument("--form-n", type=int, default=6)
    ap.add_argument("--grid-consts", action="store_true",
                    help="barrido de constantes del motor + H2H en 2024")
    ap.add_argument("--home-edge", type=float, default=0.35)
    ap.add_argument("--away-pen", type=float, default=-0.20)
    ap.add_argument("--scale", type=float, default=1.05)
    ap.add_argument("--h2h-w", type=float, default=0.0)
    args = ap.parse_args()

    for season in args.seasons:
        print(f"Cargando {args.league} {season}...", flush=True)
        matches = load_season(args.league, season)
        print(f"  {len(matches)} partidos finalizados")
        if args.grid_consts:
            for he in (0.25, 0.35, 0.45):
                for apn in (-0.10, -0.20, -0.30):
                    for sc in (1.0, 1.05, 1.10):
                        for hw in (0.0, 0.10, 0.20):
                            r = run(matches, form_n=args.form_n, home_edge=he,
                                    away_pen=apn, scale=sc, h2h_w=hw)
                            b = r["base"]
                            print(f"  he={he} ap={apn} sc={sc} h2h={hw}: "
                                  f"acc={b['acc']:.3f} brier={b['brier']:.4f} rps={b['rps']:.4f}")
        elif args.grid:
            for vs in (False, True):
                for fn in (6, 10):
                    for rho, decay in ((0.0, 0.12), (-0.12, 0.12)):
                        r = run(matches, rho=rho, decay=decay, shrink=args.shrink,
                                form_n=fn, venue_split=vs)
                        print(f"  vsplit={vs} n={fn} rho={rho} decay={decay}: "
                              f"acc base={r['base']['acc']:.3f} v2={r['v2']['acc']:.3f} | "
                              f"brier base={r['base']['brier']:.4f} v2={r['v2']['brier']:.4f} | "
                              f"rps base={r['base']['rps']:.4f} v2={r['v2']['rps']:.4f} (n={r['n']})")
        else:
            r = run(matches, rho=args.rho, decay=args.decay, shrink=args.shrink,
                    form_n=args.form_n, venue_split=args.venue_split,
                    home_edge=args.home_edge, away_pen=args.away_pen,
                    scale=args.scale, h2h_w=args.h2h_w)
            print(f"  BASE: acc={r['base']['acc']:.3f} brier={r['base']['brier']:.4f} rps={r['base']['rps']:.4f}")
            print(f"  V2:   acc={r['v2']['acc']:.3f} brier={r['v2']['brier']:.4f} rps={r['v2']['rps']:.4f} (n={r['n']})")


if __name__ == "__main__":
    main()
