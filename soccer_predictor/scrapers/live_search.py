"""
Orquestador de búsqueda en vivo: prueba cada fuente en orden y fusiona.

Orden (todas gratuitas, sin key):
  1. TheSportsDB (API libre, mejor para CUALQUIER equipo)
  2. FBref (scraping HTML, buenos promedios de goles)
  3. Noticias web (contexto: lesiones / forma)

Selenium es OPCIONAL y solo se usa si se pide explícitamente.

Devuelve un dict normalizado listo para guardar en database.py
y consumir desde prediction_engine.py.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from . import thesportsdb, fbref, web_search


def fetch_team_live(team_name: str, with_news: bool = True) -> Optional[Dict[str, Any]]:
    """Busca datos en tiempo real de CUALQUIER equipo. None si no hay nada."""
    record: Optional[Dict[str, Any]] = None
    sources_tried: List[str] = []

    # 1. TheSportsDB
    sources_tried.append("thesportsdb")
    ts = thesportsdb.fetch_team(team_name)
    if ts and ts.get("recent"):
        record = ts

    # 2. FBref como refuerzo (si el primero falló o para enriquecer)
    if record is None:
        sources_tried.append("fbref")
        fb = fbref.fetch_team(team_name)
        if fb:
            record = fb
    else:
        # si ya tenemos datos, intentamos completar fixtures con FBref sin romper
        try:
            fb = fbref.fetch_team(team_name)
            if fb and len(fb.get("fixtures", [])) >= len(record.get("fixtures", [])):
                # promediamos goles de ambas fuentes para estabilizar
                record["avg_goals_for"] = round(
                    (record.get("avg_goals_for", 0) + fb.get("avg_goals_for", 0)) / 2, 2
                )
                record["avg_goals_against"] = round(
                    (record.get("avg_goals_against", 0) + fb.get("avg_goals_against", 0)) / 2, 2
                )
                record["source"] = "thesportsdb+fbref-live"
        except Exception:
            pass

    if not record:
        return None

    # 3. Noticias (nunca rompe)
    if with_news:
        try:
            record["news"] = web_search.fetch_team_news(record.get("name", team_name))
        except Exception:
            record["news"] = {}
    record["sources_tried"] = sources_tried
    record["fetched_at"] = datetime.now(timezone.utc).isoformat()
    record["has_data"] = True
    return record


def fetch_h2h_live(team_a: str, team_b: str, limit: int = 6) -> Optional[List]:
    try:
        return thesportsdb.fetch_h2h(team_a, team_b, limit=limit)
    except Exception:
        return None
