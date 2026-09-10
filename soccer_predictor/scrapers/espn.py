"""
ESPN — API pública GRATUITA, sin key, sin registro, sin bloqueo.

Cubre las grandes ligas (incluida LaLiga `esp.1`) con datos al día:
  equipos:  https://site.api.espn.com/apis/site/v2/sports/soccer/<liga>/teams
  partidos: https://site.api.espn.com/apis/site/v2/sports/soccer/<liga>/teams/<id>/schedule?season=<año>

Es la fuente primaria para equipos de ligas top. Para equipos modestos
(Wrexham, Segunda, etc.) se sigue usando TheSportsDB como fallback.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import requests

# OJO: ESPN bloquea User-Agents largos (403). El simple 'Mozilla/5.0' funciona.
HEADERS = {"User-Agent": "Mozilla/5.0"}

# Ligas ESPN a rastrear (código ESPN -> nombre aprox). Las 4-5 primeras
# cubren el 95% de los casos; el resto solo se consulta si no hay match.
LEAGUES = [
    "esp.1",   # LaLiga
    "esp.2",   # Segunda División (LaLiga 2)
    "eng.1",   # Premier League
    "ita.1",   # Serie A
    "ger.1",   # Bundesliga
    "fra.1",   # Ligue 1
    "eng.2",   # Championship
    "ned.1",   # Eredivisie
    "por.1",   # Primeira Liga
    "eng.3",   # League One
    "eng.4",   # League Two
    "sco.1",   # Scottish Premiership
    "usa.1",   # MLS
    "mex.1",   # Liga MX
    "bra.1",   # Brasileirão
    "arg.1",   # Liga Argentina
    "uefa.champions",
    "uefa.europa",
]


def _get(url: str, params: Dict[str, Any] | None = None, timeout: int = 12):
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def _league_teams(league: str) -> List[Dict[str, Any]]:
    data = _get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/teams",
                {"limit": 100})
    if not data:
        return []
    try:
        return data["sports"][0]["leagues"][0]["teams"]
    except (KeyError, IndexError):
        return []


def _norm(s: str) -> str:
    """Minúsculas sin acentos ni espacios extra (Gijón == gijon)."""
    import unicodedata
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return " ".join(s.lower().split())


def search_team(team_name: str) -> Optional[Tuple[str, str, str]]:
    """Devuelve (league, team_id, display_name) o None."""
    q = _norm(team_name)
    fallback: Optional[Tuple[str, str, str]] = None
    for league in LEAGUES:
        for entry in _league_teams(league):
            tm = entry.get("team", {})
            name = tm.get("displayName", "")
            short = (tm.get("shortDisplayName", "") or "")
            abbr = (tm.get("abbreviation", "") or "")
            nl, sl, al = _norm(name), _norm(short), _norm(abbr)
            if nl == q or sl == q or al == q:
                return league, str(tm.get("id")), name
            if fallback is None and (q in nl or nl in q):
                fallback = (league, str(tm.get("id")), name)
    return fallback


def _seasons_to_try() -> List[int]:
    now = datetime.now()
    # Temporada europea: empieza en agosto. Ej: sept 2026 -> temporada 2026.
    cur = now.year if now.month >= 7 else now.year - 1
    return [cur, cur - 1]


def _parse_schedule(events: List[Dict[str, Any]], team_id: str) -> Tuple[str, int, int, int, List[Dict]]:
    form: List[str] = []
    gf = ga = 0
    fixtures: List[Dict] = []
    for ev in events:
        try:
            comp = (ev.get("competitions") or [{}])[0]
            state = ((comp.get("status") or {}).get("type") or {})
            if not state.get("completed"):
                continue
            competitors = comp.get("competitors") or []
            if len(competitors) < 2:
                continue
            home = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
            away = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1])
            hs = home.get("score", {}).get("value")
            as_ = away.get("score", {}).get("value")
            if hs is None or as_ is None:
                continue
            hs, as_ = int(float(hs)), int(float(as_))
            home_tid = str(home.get("team", {}).get("id") or home.get("id"))
            mine_is_home = home_tid == str(team_id)
            my, opp = (hs, as_) if mine_is_home else (as_, hs)
            form.append("W" if my > opp else ("D" if my == opp else "L"))
            gf += my
            ga += opp
            fixtures.append({
                "date": (ev.get("date") or "")[:10],
                "home": home.get("team", {}).get("displayName", ""),
                "away": away.get("team", {}).get("displayName", ""),
                "score": f"{hs}-{as_}",
                "competition": (comp.get("notes", [{}])[0].get("headline")
                                if comp.get("notes") else "") or "",
            })
        except Exception:
            continue
    return "".join(form), gf, ga, len(form), fixtures


def fetch_team(team_name: str, limit: int = 8) -> Optional[Dict[str, Any]]:
    """Devuelve dict live o None. Nunca lanza excepción."""
    try:
        found = search_team(team_name)
        if not found:
            return None
        league, team_id, display = found
        for season in _seasons_to_try():
            data = _get(
                f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league}"
                f"/teams/{team_id}/schedule",
                {"season": season},
            )
            if not data:
                continue
            events = data.get("events") or []
            # la API devuelve también futuros; nos quedamos con los jugados
            recent, gf, ga, n, fixtures = _parse_schedule(events, team_id)
            if n == 0:
                continue
            # limitamos a los últimos `limit` (vienen ordenados: futuros primero,
            # jugados después... reordenamos por fecha)
            fixtures = sorted(fixtures, key=lambda f: f.get("date", ""))[-limit:]
            # recalculamos forma/goles sobre esos últimos
            sub = fixtures
            letters = []
            gf2 = ga2 = 0
            for f in sub:
                hs, as_ = (int(x) for x in f["score"].split("-"))
                is_home = _norm(display) in _norm(f["home"]) or _norm(f["home"]) in _norm(display)
                my, opp = (hs, as_) if is_home else (as_, hs)
                letters.append("W" if my > opp else ("D" if my == opp else "L"))
                gf2 += my
                ga2 += opp
            recent = "".join(letters)
            n = len(sub)
            avg_for, avg_ag = gf2 / n, ga2 / n
            return {
                "name": display,
                "goals_for": round(avg_for * 25, 1),
                "goals_against": round(avg_ag * 25, 1),
                "recent": recent,
                "position": 10,
                "source": "espn-live",
                "has_data": True,
                "league": league,
                "season": season,
                "fixtures": fixtures,
                "avg_goals_for": round(avg_for, 2),
                "avg_goals_against": round(avg_ag, 2),
            }
        return None
    except Exception:
        return None
