"""
FBref — scraping ligero con requests + BeautifulSoup (sin Selenium).

Estrategia:
  1. Buscar equipo: https://fbref.com/en/search/search.fcgi?search=<nombre>
     - Si redirige a página de equipo, perfecto.
     - Si devuelve lista, cogemos el primer link "/en/squads/...".
  2. En la página del equipo leemos la tabla "Scores & Fixtures" para
     sacar últimos resultados (W/D/L) y goles.

Todo envuelto en try/except: si FBref bloquea o cambia el HTML -> None.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE = "https://fbref.com"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) scrapper-news"}


def _soup(url: str, timeout: int = 15) -> Optional[BeautifulSoup]:
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        return BeautifulSoup(r.text, "lxml")
    except Exception:
        return None


def resolve_team_url(team_name: str) -> Optional[str]:
    q = team_name.strip().replace(" ", "+")
    try:
        r = requests.get(f"{BASE}/en/search/search.fcgi?search={q}",
                         headers=HEADERS, timeout=15, allow_redirects=True)
        r.raise_for_status()
        # Si redirigió directamente a un squad
        if "/en/squads/" in r.url:
            return r.url
        soup = BeautifulSoup(r.text, "lxml")
        for a in soup.select("div.search-results a[href*='/en/squads/']"):
            href = a.get("href")
            if href:
                return urljoin(BASE, href)
        # fallback: cualquier link a squads
        for a in soup.select("a[href*='/en/squads/']"):
            href = a.get("href")
            if href and "/history/" not in href:
                return urljoin(BASE, href)
        return None
    except Exception:
        return None


def _parse_fixtures(soup: BeautifulSoup, limit: int = 6) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    # La tabla de partidos suele tener id con "matchlogs" o caption "Scores & Fixtures"
    table = None
    for t in soup.find_all("table"):
        cap = (t.find("caption") or "").get_text() if hasattr(t.find("caption"), "get_text") else ""
        tid = t.get("id", "")
        if "Scores" in str(cap) or "matchlogs" in tid or "fixtures" in tid.lower():
            table = t
            break
    if table is None:
        # última oportunidad: primera tabla con columnas GF/GA
        for t in soup.find_all("table"):
            th_text = t.get_text()
            if "GF" in th_text and "GA" in th_text and "Result" in th_text:
                table = t
                break
    if table is None:
        return out
    rows = table.select("tbody tr")
    for tr in rows[-limit:]:
        try:
            tds = { (td.get("data-stat") or ""): td.get_text(strip=True) for td in tr.find_all(["td", "th"]) }
            result = tds.get("result", "")
            gf = tds.get("goals_for") or tds.get("gf") or "0"
            ga = tds.get("goals_against") or tds.get("ga") or "0"
            opp = tds.get("opponent", "")
            venue = tds.get("venue", "")
            comp = tds.get("comp", "")
            date = tds.get("date", "")
            letter = result.strip().upper()[:1]
            if letter in ("W", "D", "L"):
                out.append({"date": date, "opponent": opp, "venue": venue,
                            "result": letter, "gf": gf, "ga": ga, "competition": comp})
        except Exception:
            continue
    return out


def fetch_team(team_name: str, limit: int = 6) -> Optional[Dict[str, Any]]:
    try:
        url = resolve_team_url(team_name)
        if not url:
            return None
        soup = _soup(url)
        if soup is None:
            return None
        h1 = soup.find("h1")
        real_name = h1.get_text(strip=True) if h1 else team_name
        fixtures = _parse_fixtures(soup, limit=limit)
        if len(fixtures) < 3:
            return None
        recent = "".join(f["result"] for f in fixtures)
        gf = sum(int(f["gf"]) for f in fixtures if str(f["gf"]).isdigit())
        ga = sum(int(f["ga"]) for f in fixtures if str(f["ga"]).isdigit())
        n = len(fixtures)
        avg_for, avg_ag = gf / n, ga / n
        return {
            "name": real_name,
            "goals_for": round(avg_for * 25, 1),
            "goals_against": round(avg_ag * 25, 1),
            "recent": recent,
            "position": 10,
            "source": "fbref-live",
            "has_data": True,
            "fixtures": fixtures,
            "avg_goals_for": round(avg_for, 2),
            "avg_goals_against": round(avg_ag, 2),
            "url": url,
        }
    except Exception:
        return None
