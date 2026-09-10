"""
TheSportsDB — API 100% gratuita SIN key para CUALQUIER equipo.

Endpoints usados (key pública de demo "3", válida para uso ligero):
  searchteams.php?t=<nombre>        -> resuelve idTeam
  eventslast.php?id=<idTeam>        -> últimos 5 partidos
  searchevents.php?e=A_vs_B         -> H2H aproximado

No necesita Selenium ni registro. Ideal como primera fuente live.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

import requests

BASE = "https://www.thesportsdb.com/api/v1/json/3"
HEADERS = {"User-Agent": "Mozilla/5.0 (scrapper-news soccer-predictor)"}


def _get(path: str, params: Dict[str, Any], timeout: int = 12):
    try:
        r = requests.get(f"{BASE}/{path}", params=params, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def search_team(team_name: str) -> Optional[Dict[str, Any]]:
    data = _get("searchteams.php", {"t": team_name})
    if not data:
        return None
    teams = data.get("teams") or []
    if not teams:
        return None
    # mejor match: nombre más parecido
    q = team_name.strip().lower()
    def score(t):
        name = (t.get("strTeam") or "").lower()
        if name == q:
            return 0
        if q in name or name in q:
            return 1
        return 2
    teams.sort(key=score)
    t = teams[0]
    return {
        "id": t.get("idTeam"),
        "name": t.get("strTeam"),
        "league": t.get("strLeague"),
        "country": t.get("strCountry"),
    }


def last_events(team_id: str, limit: int = 6) -> List[Dict[str, Any]]:
    data = _get("eventslast.php", {"id": team_id})
    if not data:
        return []
    return (data.get("results") or [])[:limit]


def _to_recent(events: List[Dict[str, Any]], team_name: str) -> str:
    form = []
    for ev in events:
        hs = ev.get("intHomeScore")
        as_ = ev.get("intAwayScore")
        if hs is None or as_ is None:
            continue
        try:
            hs, as_ = int(hs), int(as_)
        except (TypeError, ValueError):
            continue
        home = (ev.get("strHomeTeam") or "").lower()
        is_home = team_name.lower() in home or home in team_name.lower()
        gf, ga = (hs, as_) if is_home else (as_, hs)
        form.append("W" if gf > ga else ("D" if gf == ga else "L"))
    # eventslast viene del más reciente al más antiguo -> invertimos
    # para que el último char sea el partido más reciente (nuestro formato)
    form = list(reversed(form))
    return "".join(form)


def fetch_team(team_name: str) -> Optional[Dict[str, Any]]:
    """Devuelve dict live o None. Nunca lanza excepción."""
    try:
        found = search_team(team_name)
        if not found:
            return None
        events = last_events(str(found["id"]))
        if not events:
            return None
        recent = _to_recent(events, found["name"])
        gf = ga = 0
        n = 0
        fixtures = []
        for ev in events:
            hs, as_ = ev.get("intHomeScore"), ev.get("intAwayScore")
            if hs is None or as_ is None:
                continue
            try:
                hs, as_ = int(hs), int(as_)
            except (TypeError, ValueError):
                continue
            home = ev.get("strHomeTeam") or ""
            is_home = found["name"].lower() in home.lower()
            my, opp = (hs, as_) if is_home else (as_, hs)
            gf += my
            ga += opp
            n += 1
            fixtures.append({
                "date": ev.get("dateEvent"),
                "home": home,
                "away": ev.get("strAwayTeam"),
                "score": f"{hs}-{as_}",
                "competition": ev.get("strLeague"),
            })
        if n == 0:
            return None
        # normalizamos a "por 25 partidos" para que encaje con el motor actual
        # (el motor divide goals_for/25). Usamos proyección simple.
        avg_for = gf / n
        avg_against = ga / n
        return {
            "name": found["name"],
            "goals_for": round(avg_for * 25, 1),
            "goals_against": round(avg_against * 25, 1),
            "recent": recent,
            "position": 10,
            "source": "thesportsdb-live",
            "has_data": True,
            "league": found.get("league"),
            "fixtures": fixtures,
            "avg_goals_for": round(avg_for, 2),
            "avg_goals_against": round(avg_against, 2),
        }
    except Exception:
        return None


def fetch_h2h(team_a: str, team_b: str, limit: int = 6) -> Optional[List]:
    """H2H vía searchevents 'A_vs_B'. Formato compatible con el motor."""
    try:
        for query in (f"{team_a}_vs_{team_b}", f"{team_b}_vs_{team_a}"):
            data = _get("searchevents.php", {"e": query})
            if not data:
                continue
            events = data.get("event") or []
            out = []
            for ev in events[:limit]:
                hs, as_ = ev.get("intHomeScore"), ev.get("intAwayScore")
                try:
                    hs = int(hs) if hs is not None else 0
                    as_ = int(as_) if as_ is not None else 0
                except (TypeError, ValueError):
                    continue
                out.append([
                    ev.get("strHomeTeam") or team_a,
                    ev.get("strAwayTeam") or team_b,
                    hs, as_,
                    ev.get("strLeague") or "",
                ])
            if out:
                return out
        return None
    except Exception:
        return None
