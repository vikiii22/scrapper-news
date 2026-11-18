"""Helper HTTP compartido por los adaptadores (fácil de monkeypatchear)."""

from __future__ import annotations

from typing import Any, Dict, Optional

import requests

HEADERS = {"User-Agent": "Mozilla/5.0"}


def get_text(url: str, params: Optional[Dict[str, Any]] = None,
             timeout: int = 20) -> str:
    response = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
    response.raise_for_status()
    try:
        return response.content.decode("utf-8-sig")
    except UnicodeDecodeError:
        return response.content.decode("latin-1")
