"""Ejecución única: jornada de Losilla + contexto + análisis + informe."""

from __future__ import annotations

import argparse
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from . import database
    from .boleto import build_boleto, pleno_variants
    from .orchestrator import predict
    from .quiniela import pleno_suggestion
    from .quiniela_sources import (clubelo, football_data, injuries, losilla,
                                   markets, news, understat)
    from .quiniela_sources.cache import Cache
    from .report import write_report
    from .scrapers import espn
except ImportError:  # pragma: no cover
    import database
    from boleto import build_boleto, pleno_variants
    from orchestrator import predict
    from quiniela import pleno_suggestion
    from quiniela_sources import (clubelo, football_data, injuries, losilla,
                                  markets, news, understat)
    from quiniela_sources.cache import Cache
    from report import write_report
    from scrapers import espn

BASE_DIR = Path(__file__).resolve().parent.parent
UNIFORM = {"1": 100.0 / 3, "X": 100.0 / 3, "2": 100.0 / 3}

# Alias de módulo para poder sustituirlo en tests o integrarlo en otro flujo.
fetch_jornada = losilla.fetch_jornada


def competition_for(match: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> str:
    if match.get("is_women"):
        return "Liga F"
    league = (context or {}).get("league")
    if league == "esp.2":
        return "Segunda División"
    if league == "esp.1":
        return "La Liga"
    return "Fútbol"


def _form_from_predict(match: Dict[str, Any], result: Dict[str, Any]) -> None:
    context = match.setdefault("context", {})
    if (context.get("form") or {}).get("home"):
        return
    sources = result.get("data_sources") or {}
    home = sources.get("home_recent")
    away = sources.get("away_recent")
    if home or away:
        context["form"] = {"home": {"recent": (home or "")[-5:]},
                           "away": {"recent": (away or "")[-5:]}}


def analyze_matches(entry: Dict[str, Any], predict_fn=predict,
                    contexts: Optional[Dict[int, Dict[str, Any]]] = None,
                    fast: bool = False, persist: bool = False) -> Dict[str, Any]:
    contexts = contexts or {}
    for match in entry.get("matches", []):
        n = int(match.get("n", 0))
        context = contexts.get(n) or {}
        competition = competition_for(match, context)
        absences = {}
        for side in ("home", "away"):
            info = (context.get("injuries") or {}).get(side) or {}
            absences[side] = info.get("count") if info.get("ok") else None
        match["context"] = context
        match["competition"] = competition
        match["absences"] = absences

        try:
            result = predict_fn(
                match.get("home", ""),
                match.get("away", ""),
                competition,
                live=True,
                with_news=False,
                player_form=not fast,
                absences_home=absences["home"] or 0,
                absences_away=absences["away"] or 0,
                women=bool(match.get("is_women")),
                log=False,
                explain=False,
                persist=persist,
            )
        except Exception as exc:
            result = None
            match["model_error"] = str(exc)

        if result:
            probs = result.get("prob_1x2") or {}
            match["modelo"] = {
                "1": round(float(probs.get("home", 0)) * 100, 1),
                "X": round(float(probs.get("draw", 0)) * 100, 1),
                "2": round(float(probs.get("away", 0)) * 100, 1),
            }
            match["pick"] = result.get("prediction_1x2")
            match["expected_goals"] = result.get("expected_goals")
            match["low_confidence"] = bool(result.get("low_confidence"))
            match["positions"] = result.get("positions")
            match["data_sources"] = result.get("data_sources")
            _form_from_predict(match, result)
        else:
            reference = match.get("lae") or match.get("probables") or UNIFORM
            match["modelo"] = {sign: float(reference.get(sign, 0) or 0) for sign in ("1", "X", "2")}
            match["pick"] = max(("1", "X", "2"), key=lambda sign: match["modelo"][sign])
            match["expected_goals"] = None
            match["low_confidence"] = True

        if n == 15:
            match["valor"] = None
            match["value_pick"] = None
            goals = match.get("expected_goals")
            if goals and goals.get("home") is not None and goals.get("away") is not None:
                match["pleno_sugerido"] = pleno_suggestion(
                    float(goals["home"]), float(goals["away"])
                )
        else:
            reference = match.get("lae") or match.get("probables") or UNIFORM
            match["valor"] = {
                sign: round(match["modelo"].get(sign, 0) - float(reference.get(sign, 0) or 0), 1)
                for sign in ("1", "X", "2")
            }
            best = max(match["valor"], key=lambda sign: match["valor"][sign])
            match["value_pick"] = best if match["valor"][best] >= 3 else None

    pleno = next((m for m in entry.get("matches", []) if m.get("n") == 15), None)
    goals = (pleno or {}).get("expected_goals")
    if goals and goals.get("home") is not None and goals.get("away") is not None:
        entry["pleno_variants"] = pleno_variants(
            float(goals["home"]), float(goals["away"])
        )
    return entry


def _context_for(match: Dict[str, Any], fd_rows: Dict[str, List[Dict[str, Any]]],
                 cache: Optional[Cache]) -> tuple[int, Dict[str, Any]]:
    home, away = match.get("home", ""), match.get("away", "")
    women = bool(match.get("is_women"))
    context: Dict[str, Any] = {
        "league": None,
        "form": {},
        "injuries": {},
        "news": {},
        "elo": {"home": None, "away": None},
    }

    try:
        found = espn.search_team(home, women=women) or espn.search_team(away, women=women)
        if found:
            context["league"] = found[0]
    except Exception:
        pass

    league = context["league"]
    code = {"esp.1": "SP1", "esp.2": "SP2"}.get(league)
    if code and fd_rows.get(code):
        rows = fd_rows[code]
        try:
            home_form = football_data.team_form(rows, home, venue="home")
            away_form = football_data.team_form(rows, away, venue="away")
            if not home_form["matches"]:
                home_form = football_data.team_form(rows, home)
            if not away_form["matches"]:
                away_form = football_data.team_form(rows, away)
            context["form"] = {"home": home_form, "away": away_form}
        except Exception:
            context["form"] = {}
        try:
            context["odds"] = football_data.closing_odds(rows, home, away)
        except Exception:
            context["odds"] = None

    try:
        context["injuries"] = {
            "home": injuries.fetch_injuries(home, women=women, cache=cache),
            "away": injuries.fetch_injuries(away, women=women, cache=cache),
        }
    except Exception:
        context["injuries"] = {}

    try:
        query = f"{home} {away}" + (" femenino" if women else "")
        context["news"] = news.headlines(query, cache=cache)
    except Exception:
        context["news"] = {}

    if women:
        # ClubElo no distingue equipos femeninos: no mezclar Elo masculino.
        context["elo"] = {"home": None, "away": None}
    else:
        try:
            context["elo"] = {
                "home": clubelo.elo(home, cache=cache).get("elo"),
                "away": clubelo.elo(away, cache=cache).get("elo"),
            }
        except Exception:
            context["elo"] = {"home": None, "away": None}

    return int(match.get("n", 0)), context


def build_contexts(matches: List[Dict[str, Any]],
                   cache: Optional[Cache] = None) -> Dict[int, Dict[str, Any]]:
    fd_rows: Dict[str, List[Dict[str, Any]]] = {}
    for code in ("SP1", "SP2"):
        loaded = football_data.load_league(code, cache=cache)
        if loaded.get("ok"):
            fd_rows[code] = loaded.get("rows") or []

    contexts: Dict[int, Dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(_context_for, match, fd_rows, cache) for match in matches]
        for future in futures:
            try:
                n, context = future.result()
                contexts[n] = context
            except Exception:
                continue
    return contexts


def _display_name(match: Dict[str, Any]) -> str:
    suffix = " (F)" if match.get("is_women") else ""
    return f"{match.get('home', '?')}-{match.get('away', '?')}{suffix}"


def _is_closed(close: str, now: Optional[datetime] = None) -> Optional[bool]:
    """True/False si el cierre es interpretable; None si no se puede saber."""
    now = now or datetime.now()
    match = re.search(r"(\d{1,2})/(\d{1,2})", close or "")
    hour = re.search(r"(\d{1,2}):(\d{2})", close or "")
    if not match or not hour:
        return None
    day, month = int(match.group(1)), int(match.group(2))
    year = now.year
    if month < now.month - 6:
        year += 1
    try:
        deadline = datetime(year, month, day, int(hour.group(1)), int(hour.group(2)))
    except ValueError:
        return None
    return now >= deadline


def _sources_summary(contexts: Dict[int, Dict[str, Any]],
                     understat_result: Dict[str, Any],
                     markets_result: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    values = list(contexts.values())
    return {
        "losilla": {"ok": True, "note": "CSV + HTML del boleto"},
        "espn": {"ok": any(v.get("league") for v in values), "note": "forma y liga"},
        "football_data": {"ok": any(v.get("form") for v in values), "note": "SP1/SP2"},
        "transfermarkt": {
            "ok": any((v.get("injuries", {}).get("home") or {}).get("ok") for v in values),
            "note": "bajas y sanciones",
        },
        "understat": {"ok": bool(understat_result.get("ok")),
                      "note": understat_result.get("error") or ""},
        "clubelo": {
            "ok": any((v.get("elo") or {}).get("home") is not None for v in values),
            "note": "Elo",
        },
        "markets": {"ok": bool(markets_result.get("ok")),
                    "note": markets_result.get("error") or ""},
        "news": {"ok": any((v.get("news") or {}).get("ok") for v in values),
                 "note": "Google News"},
    }


def run(jornada: Optional[int] = None, html: Optional[str] = None,
        force: bool = False, save: bool = False,
        output_dir: Path = Path("output"), fast: bool = False,
        predict_fn=None, no_cache: bool = False) -> Dict[str, Any]:
    cache = None if no_cache else Cache(
        BASE_DIR / "data" / "cache" / f"jornada_{jornada or 'auto'}",
        max_age_hours=6,
    )
    entry = fetch_jornada(jornada=jornada, html=html, cache=cache)
    if len(entry.get("matches") or []) != 15:
        return {"error": "jornada_incompleta", "jornada": entry.get("jornada")}

    closed = _is_closed(entry.get("close", ""))
    if closed is None and not force:
        return {"error": "cierre_desconocido", "jornada": entry.get("jornada"),
                "close": entry.get("close")}
    if (entry.get("played") or closed) and not force:
        return {"error": "jornada_no_jugable", "jornada": entry.get("jornada"),
                "close": entry.get("close")}
    if force and (closed is None or closed or entry.get("played")):
        entry["forced"] = True

    contexts = build_contexts(entry["matches"], cache=cache)
    entry = analyze_matches(entry, predict_fn=predict_fn or predict,
                            contexts=contexts, fast=fast, persist=save)
    entry["boleto_rentable"] = build_boleto(entry["matches"], "rentable")
    entry["boleto_conservador"] = build_boleto(entry["matches"], "seguro")

    understat_result = understat.league_xg("La_liga", cache=cache)
    markets_result = markets.outright_context(cache=cache)
    entry["sources"] = _sources_summary(contexts, understat_result, markets_result)

    markdown_path, json_path = write_report(entry, output_dir)
    entry["report_paths"] = {"markdown": str(markdown_path), "json": str(json_path)}

    if save:
        try:
            database.save_quiniela(entry["jornada"], entry["matches"])
        except Exception as exc:
            entry["save_error"] = str(exc)
    return entry


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Analiza la jornada vigente de la quiniela y genera dos boletos."
    )
    parser.add_argument("--jornada", type=int, default=None)
    parser.add_argument("--html", type=str, default=None,
                        help="HTML del boleto guardado (respaldo sin red)")
    parser.add_argument("--force", action="store_true",
                        help="analiza aunque el cierre haya pasado")
    parser.add_argument("--save", action="store_true",
                        help="guarda también en la BBDD existente")
    parser.add_argument("--fast", action="store_true",
                        help="omite la forma de jugadores para ir más rápido")
    parser.add_argument("--output", type=str, default="output")
    parser.add_argument("--no-cache", action="store_true")
    args = parser.parse_args(argv)

    html = None
    try:
        if args.html:
            html = Path(args.html).read_text(encoding="utf-8-sig")
        result = run(
            jornada=args.jornada,
            html=html,
            force=args.force,
            save=args.save,
            output_dir=Path(args.output),
            fast=args.fast,
            no_cache=args.no_cache,
        )
    except Exception as exc:
        print(f"Error: {exc}")
        return 1

    if result.get("error"):
        if result["error"] == "jornada_no_jugable":
            print(
                f"La jornada {result.get('jornada')} ya ha cerrado "
                f"({result.get('close', '')}). Usa --force para analizarla igual "
                "o --jornada N para la siguiente."
            )
        elif result["error"] == "cierre_desconocido":
            print(
                "No se pudo determinar la hora de cierre del boleto. "
                "Usa --jornada N o --force para analizarla igualmente."
            )
        else:
            print(f"Error: {result['error']}")
        return 2

    print(f"Jornada {result['jornada']} — {result.get('close', '')}")
    print(f"Informe: {result['report_paths']['markdown']}")
    for key in ("boleto_rentable", "boleto_conservador"):
        boleto = result[key]
        multiples = boleto.get("multiples") or {}
        print(
            f"\n{boleto['name']}: {boleto['bets']} apuestas, "
            f"{boleto['cost_eur']:.2f} €, pleno "
            f"{boleto['pleno'].get('home')}-{boleto['pleno'].get('away')}"
        )
        print(
            f"  Triples: {multiples.get('triples')} · Dobles: {multiples.get('dobles')}"
        )
        for n in range(1, 15):
            signs = boleto["signs"].get(n) or boleto["signs"].get(str(n)) or []
            name = next(
                (_display_name(m) for m in result["matches"]
                 if int(m.get("n", 0)) == n),
                "",
            )
            print(f"  {n:2d}. {name:<32} {' '.join(signs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
