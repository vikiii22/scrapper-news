"""
Clasificación (posición en la tabla) calculada desde calendarios ESPN.

ESPN no expone tabla en su API pública, así que la construimos:
todos los calendarios de la liga (con caché 24h en disco) -> W/D/L,
goles y puntos, ordenados como una clasificación oficial.

Cubre las mismas ligas que el scraper ESPN (esp.1, esp.2, esp.w.1, ...).
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CACHE_DIR = BASE_DIR / "data" / "db" / "cache"
CACHE_TTL_H = 24


def _cache_path(league: str, season: int) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"standings_{league.replace('.', '_')}_{season}.json"


def get_table(league: str, season: Optional[int] = None) -> List[Dict[str, Any]]:
    """Devuelve la tabla [{pos, team_id, team, played, won, drawn, lost,
    gf, ga, pts}] o [] si no se puede construir."""
    try:
        from . import espn
    except ImportError:
        import espn
    if season is None:
        season = espn._seasons_to_try()[0]
    cp = _cache_path(league, season)
    if cp.exists() and (time.time() - cp.stat().st_mtime) < CACHE_TTL_H * 3600:
        try:
            return json.loads(cp.read_text(encoding="utf-8"))
        except Exception:
            pass
    table: Dict[str, Dict[str, Any]] = {}
    try:
        teams = espn._league_teams(league)
        seen = set()
        for entry in teams:
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
                key = str(ev.get("id"))
                if key in seen:
                    continue
                seen.add(key)
                home = next((c for c in cs if c.get("homeAway") == "home"), cs[0])
                away = next((c for c in cs if c.get("homeAway") == "away"), cs[1])
                try:
                    hs = int(float(home["score"]["value"]))
                    as_ = int(float(away["score"]["value"]))
                except (KeyError, TypeError, ValueError):
                    continue
                for side, tid_s, gf, ga in (
                        ("h", str(home.get("team", {}).get("id")), hs, as_),
                        ("a", str(away.get("team", {}).get("id")), as_, hs)):
                    row = table.setdefault(tid_s, {
                        "team_id": tid_s,
                        "team": side and (home if side == "h" else away).get("team", {}).get("displayName", "?"),
                        "played": 0, "won": 0, "drawn": 0, "lost": 0,
                        "gf": 0, "ga": 0, "pts": 0})
                    row["played"] += 1
                    row["gf"] += gf
                    row["ga"] += ga
                    if gf > ga:
                        row["won"] += 1
                        row["pts"] += 3
                    elif gf == ga:
                        row["drawn"] += 1
                        row["pts"] += 1
                    else:
                        row["lost"] += 1
    except Exception:
        return []
    rows = sorted(table.values(),
                  key=lambda r: (-r["pts"], -(r["gf"] - r["ga"]), -r["gf"]))
    for i, r in enumerate(rows, 1):
        r["pos"] = i
        r["gd"] = r["gf"] - r["ga"]
    try:
        cp.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass
    return rows


def position_of(team_name: str, league: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """{'pos': 5, 'pts': 12, 'played': 5, ...} o None. Nunca lanza excepción."""
    try:
        from . import espn
    except ImportError:
        import espn
    try:
        if league:
            leagues = [league]
        else:
            found = espn.search_team(team_name)
            if not found:
                return None
            leagues = [found[0]]
        for lg in leagues:
            table = get_table(lg)
            if not table:
                continue
            # 1) por id exacto
            tid = None
            try:
                f = espn.search_team(team_name)
                if f and f[0] == lg:
                    tid = f[1]
            except Exception:
                pass
            for row in table:
                if tid and row["team_id"] == tid:
                    return row
            # 2) por nombre aproximado
            q = espn._norm(team_name)
            for row in table:
                rn = espn._norm(row["team"])
                if q == rn or q in rn or rn in q:
                    return row
        return None
    except Exception:
        return None
