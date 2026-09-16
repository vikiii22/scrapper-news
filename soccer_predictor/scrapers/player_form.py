"""
Racha de goleadores vía OpenLigaDB (gratuito, sin key).

Cada partido trae la lista de goles con `goalGetterName`, así que podemos
calcular qué jugadores llegan en racha (goles en los últimos N partidos
del equipo) para las ligas cubiertas por OpenLigaDB
(LaLiga `la1`, Bundesliga `bl1`, Premier `pl`, ...).

Las bajas (lesionados/sancionados) NO tienen fuente gratuita estructurada
fiable en fútbol (el endpoint de ESPN devuelve vacío), así que van por
entrada manual (`key_absences`) en CLI/app y quedan registradas en el JSON.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CACHE_DIR = BASE_DIR / "data" / "db" / "cache"
CACHE_TTL_H = 24

# Candidatas OpenLigaDB (shortcut -> temporada). Se prueban en orden.
LEAGUE_SHORTCUTS = ["la1", "bl1", "pl", "sa", "bl2", "lig1", "cl", "uel2026"]


def _season_year() -> int:
    import datetime
    now = datetime.datetime.now()
    return now.year if now.month >= 7 else now.year - 1


def _season_matches(shortcut: str, year: int) -> List[Dict[str, Any]]:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache = CACHE_DIR / f"openligadb_{shortcut}_{year}.json"
    if cache.exists() and (time.time() - cache.stat().st_mtime) < CACHE_TTL_H * 3600:
        try:
            return json.loads(cache.read_text(encoding="utf-8"))
        except Exception:
            pass
    try:
        r = requests.get(f"https://api.openligadb.de/getmatchdata/{shortcut}/{year}",
                         timeout=30)
        r.raise_for_status()
        data = r.json()
        cache.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return data
    except Exception:
        return []


def _team_matches(all_matches: List[Dict], team_name: str) -> List[Dict]:
    q = team_name.strip().lower()
    out = []
    for m in all_matches:
        if not m.get("matchIsFinished"):
            continue
        t1 = m.get("team1", {}).get("teamName", "")
        t2 = m.get("team2", {}).get("teamName", "")
        if q in t1.lower() or t1.lower() in q or q in t2.lower() or t2.lower() in q:
            out.append(m)
    return sorted(out, key=lambda m: m.get("matchDateTime", ""))


def hot_scorers(team_name: str, last_n: int = 5) -> Dict[str, Any]:
    """
    Devuelve {'scorers': [{'name':..,'goals':..}], 'league': shortcut|None,
              'matches_analyzed': int}.
    Nunca lanza excepción; si no hay cobertura, scorers=[].
    """
    year = _season_year()
    try:
        for shortcut in LEAGUE_SHORTCUTS:
            matches = _season_matches(shortcut, year)
            if not matches:
                continue
            mine = _team_matches(matches, team_name)
            if len(mine) < 2:
                continue
            recent = mine[-last_n:]
            tally: Dict[str, int] = {}
            for m in recent:
                t1 = m.get("team1", {}).get("teamName", "")
                t2 = m.get("team2", {}).get("teamName", "")
                q = team_name.strip().lower()
                mine_is_t1 = q in t1.lower() or t1.lower() in q
                my_id = m.get("team1", {}).get("teamId") if mine_is_t1 else m.get("team2", {}).get("teamId")
                for g in m.get("goals") or []:
                    if g.get("isOwnGoal"):
                        continue
                    if my_id and g.get("scoringTeamId") != my_id:
                        continue
                    name = (g.get("goalGetterName") or "").strip()
                    if name:
                        tally[name] = tally.get(name, 0) + 1
            scorers = sorted(
                ({"name": k, "goals": v} for k, v in tally.items()),
                key=lambda s: -s["goals"],
            )[:3]
            return {"scorers": scorers, "league": shortcut,
                    "matches_analyzed": len(recent)}
    except Exception:
        pass
    return {"scorers": [], "league": None, "matches_analyzed": 0}
