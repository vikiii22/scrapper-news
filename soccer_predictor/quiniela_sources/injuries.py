"""Transfermarkt: lesionados y sancionados por equipo."""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional
from unicodedata import normalize
from urllib.parse import quote, urljoin

from bs4 import BeautifulSoup

from .cache import Cache
from .http import get_text

BASE_URL = "https://www.transfermarkt.es"
SEARCH_URL = f"{BASE_URL}/schnellsuche/ergebnis/schnellsuche"


def _get_text(url: str, params: Optional[Dict[str, Any]] = None,
              timeout: int = 15) -> str:
    return get_text(url, params=params, timeout=timeout)


def _norm(value: str) -> str:
    text = normalize("NFKD", value or "").encode("ascii", "ignore").decode()
    return " ".join(text.lower().split())


def _int(value: str) -> Optional[int]:
    digits = "".join(ch for ch in (value or "") if ch.isdigit())
    return int(digits) if digits else None


def parse_injuries_html(html: str) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html or "", "lxml")
    table = soup.select_one("table.items")
    if not table:
        return []

    players: List[Dict[str, Any]] = []
    tbody = table.find("tbody")
    rows = tbody.find_all("tr", recursive=False) if tbody else []
    for row in rows:
        link = row.select_one("td.hauptlink a[href*='/profil/spieler/']")
        if not link:
            continue
        name = link.get_text(" ", strip=True)
        position_cell = row.select_one("table.inline-table tr:nth-child(2) td")
        position = position_cell.get_text(" ", strip=True) if position_cell else ""

        issue_cell = row.select_one("td.links.hauptlink") or row.select_one("td.links")
        issue = issue_cell.get_text(" ", strip=True) if issue_cell else ""

        centered = [td.get_text(" ", strip=True) for td in row.select("td.zentriert")]
        dates = [value for value in centered if "/" in value]
        since = dates[0] if dates else ""
        until = dates[1] if len(dates) > 1 else ""
        matches_out = _int(centered[-1]) if centered else None

        if not issue:
            candidates = [td.get_text(" ", strip=True) for td in row.select("td")]
            issue = max(candidates, key=len) if candidates else ""

        players.append({
            "name": name,
            "position": position,
            "issue": issue,
            "since": since,
            "until": until,
            "matches_out": matches_out,
        })
    return players


def resolve_team_url(team: str) -> Optional[str]:
    html = _get_text(SEARCH_URL, params={"query": team})
    soup = BeautifulSoup(html, "lxml")
    best_url = None
    best_score = 0.0
    seen = set()
    for link in soup.select("a[href*='/verein/']"):
        href = link.get("href") or ""
        if "startseite/verein/" not in href or href in seen:
            continue
        seen.add(href)
        name = link.get_text(" ", strip=True)
        score = SequenceMatcher(None, _norm(team), _norm(name)).ratio()
        if score > best_score:
            best_score = score
            best_url = urljoin(BASE_URL, href)
    return best_url if best_score >= 0.6 else None


def fetch_injuries(team: str, women: bool = False,
                   cache: Optional[Cache] = None,
                   timeout: int = 12) -> Dict[str, Any]:
    if women:
        return {"ok": False, "players": [], "count": 0,
                "error": "sin cobertura femenina en Transfermarkt",
                "source_url": None}

    key = f"injuries_{team}"
    if cache is not None:
        cached = cache.get(key)
        if cached:
            return cached

    result: Dict[str, Any]
    try:
        team_url = resolve_team_url(team)
        if not team_url:
            result = {"ok": False, "players": [], "count": 0,
                      "error": "equipo no encontrado", "source_url": None}
        else:
            injuries_url = team_url.replace("/startseite/", "/sperrenundverletzungen/")
            html = _get_text(injuries_url, timeout=timeout)
            players = parse_injuries_html(html)
            result = {"ok": True, "players": players, "count": len(players),
                      "error": None, "source_url": injuries_url}
    except Exception as exc:
        result = {"ok": False, "players": [], "count": 0,
                  "error": str(exc), "source_url": None}

    if cache is not None:
        cache.set(key, result)
    return result
