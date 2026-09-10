"""
Búsqueda web ligera (sin API key, sin Selenium).

Usa el HTML público de DuckDuckGo para recoger contexto reciente:
  - noticias del equipo ("<equipo> lesiones sancionados once")
  - forma/reciente ("<equipo> últimos resultados")

No es un dato estadístico duro: se guarda como `news` en la BBDD JSON
y sirve de contexto para el pronóstico / explicación.
"""

from __future__ import annotations

from typing import Any, Dict, List
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (scrapper-news soccer-predictor)"}
DDG = "https://html.duckduckgo.com/html/"


def search(query: str, limit: int = 5) -> List[Dict[str, str]]:
    try:
        r = requests.post(DDG, data={"q": query}, headers=HEADERS, timeout=12)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        out = []
        for res in soup.select(".result")[:limit]:
            title_el = res.select_one(".result__title a") or res.select_one("a.result__a")
            snip_el = res.select_one(".result__snippet")
            title = title_el.get_text(strip=True) if title_el else ""
            url = title_el.get("href", "") if title_el else ""
            snippet = snip_el.get_text(strip=True) if snip_el else ""
            if title:
                out.append({"title": title, "url": url, "snippet": snippet})
        return out
    except Exception:
        return []


def fetch_team_news(team_name: str) -> Dict[str, Any]:
    injuries = search(f"{team_name} lesionados sancionados convocatoria", limit=4)
    form = search(f"{team_name} últimos resultados forma", limit=4)
    return {
        "injuries_news": injuries,
        "form_news": form,
    }
