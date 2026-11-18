"""ClubElo: Elo por equipo. Best-effort (el servicio es inestable)."""

from __future__ import annotations

from typing import Any, Dict, Optional
from urllib.parse import quote

from .cache import Cache
from .http import get_text

BASE_URL = "http://api.clubelo.com"


def _get_text(url: str, timeout: int = 8) -> str:
    return get_text(url, timeout=timeout)


def elo(team: str, cache: Optional[Cache] = None,
        timeout: int = 8) -> Dict[str, Any]:
    key = f"clubelo_{team}"
    if cache is not None:
        cached = cache.get(key)
        if cached:
            return cached

    result: Dict[str, Any]
    try:
        text = _get_text(f"{BASE_URL}/{quote(team)}", timeout=timeout)
        lines = [line for line in text.splitlines() if line.strip()]
        if len(lines) < 2:
            result = {"ok": False, "elo": None, "error": "respuesta vacía"}
        else:
            fields = lines[-1].split(",")
            value = float(fields[4]) if len(fields) > 4 else None
            result = {"ok": value is not None, "elo": value,
                      "error": None if value is not None else "sin Elo"}
    except Exception as exc:
        result = {"ok": False, "elo": None, "error": str(exc)}

    if cache is not None:
        cache.set(key, result)
    return result
