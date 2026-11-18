"""Understat: xG/xGA por equipo. Best-effort (el sitio puede bloquear)."""

from __future__ import annotations

import codecs
import json
import re
from typing import Any, Dict, Optional
from urllib.parse import quote

from .cache import Cache
from .http import get_text

BASE_URL = "https://understat.com/league"


def _get_text(url: str, timeout: int = 12) -> str:
    return get_text(url, timeout=timeout)


def league_xg(league: str = "La_liga", cache: Optional[Cache] = None,
              timeout: int = 12) -> Dict[str, Any]:
    key = f"understat_{league}"
    if cache is not None:
        cached = cache.get(key)
        if cached and cached.get("ok"):
            return cached

    result: Dict[str, Any]
    try:
        html = _get_text(f"{BASE_URL}/{quote(league)}", timeout=timeout)
        match = re.search(r"teamsData\s*=\s*JSON\.parse\('(.+?)'\)", html, re.S)
        if not match:
            result = {"ok": False, "teams": {}, "error": "sin teamsData"}
        else:
            payload = json.loads(codecs.decode(match.group(1), "unicode_escape"))
            teams: Dict[str, Any] = {}
            for row in payload.values():
                title = row.get("title")
                history = row.get("history") or []
                if not title or not history:
                    continue
                last = history[-1]
                teams[title] = {
                    "xg": float(last.get("xG", 0) or 0),
                    "xga": float(last.get("xGA", 0) or 0),
                    "xpts": float(last.get("xPTS", 0) or 0),
                }
            result = {"ok": bool(teams), "teams": teams,
                      "error": None if teams else "sin equipos"}
    except Exception as exc:
        result = {"ok": False, "teams": {}, "error": str(exc)}

    if cache is not None and result.get("ok"):
        cache.set(key, result)
    return result
