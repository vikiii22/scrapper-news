"""
Orquestador de búsqueda en vivo: prueba cada fuente en orden y fusiona.

Orden (todas gratuitas, sin key):
  1. ESPN (API pública, datos al día en ligas top: LaLiga, Premier, etc.)
  2. TheSportsDB (API libre, mejor para equipos modestos / cualquier equipo)
  3. FBref (scraping HTML, buenos promedios de goles)
  4. Noticias web (contexto: lesiones / forma)

Selenium es OPCIONAL y solo se usa si se pide explícitamente.

Devuelve un dict normalizado listo para guardar en database.py
y consumir desde prediction_engine.py.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from . import thesportsdb, web_search, espn


def fetch_team_live(team_name: str, with_news: bool = True) -> Optional[Dict[str, Any]]:
    """Busca datos en tiempo real de CUALQUIER equipo. None si no hay nada."""
    record: Optional[Dict[str, Any]] = None
    sources_tried: List[str] = []

    # 1. ESPN (la más al día para ligas top)
    sources_tried.append("espn")
    try:
        record = espn.fetch_team(team_name)
    except Exception:
        record = None

    # 2. TheSportsDB (cubre equipos modestos de cualquier país)
    if not record or len(record.get("recent", "")) < 2:
        sources_tried.append("thesportsdb")
        try:
            ts = thesportsdb.fetch_team(team_name)
        except Exception:
            ts = None
        if ts and ts.get("recent"):
            # nos quedamos con la fuente que tenga MÁS partidos reales
            if not record or len(ts.get("recent", "")) > len(record.get("recent", "")):
                record = ts

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
