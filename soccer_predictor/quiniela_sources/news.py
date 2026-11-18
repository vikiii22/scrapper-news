"""Google News RSS: titulares recientes por partido."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from .cache import Cache
from .http import get_text

BASE_URL = "https://news.google.com/rss/search"


def _get_text(url: str, params: Optional[Dict[str, Any]] = None,
              timeout: int = 10) -> str:
    return get_text(url, params=params, timeout=timeout)


def parse_rss(xml: str, limit: int = 3) -> List[Dict[str, str]]:
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return []

    items: List[Dict[str, str]] = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        if not title:
            continue
        source_el = item.find("source")
        source = ""
        if source_el is not None:
            source = (source_el.text or "").strip()
        items.append({
            "title": title,
            "date": (item.findtext("pubDate") or "").strip(),
            "source": source,
        })
        if len(items) >= limit:
            break
    return items


def headlines(query: str, limit: int = 3, cache: Optional[Cache] = None,
              timeout: int = 10) -> Dict[str, Any]:
    key = f"news_{query}_{limit}"
    if cache is not None:
        cached = cache.get(key)
        if cached and cached.get("ok"):
            return cached

    url = f"{BASE_URL}?q={quote(query)}&hl=es&gl=ES&ceid=ES:es"
    try:
        xml = _get_text(url, timeout=timeout)
        items = parse_rss(xml, limit=limit)
        result = {"ok": bool(items), "items": items, "error": None}
    except Exception as exc:
        result = {"ok": False, "items": [], "error": str(exc)}

    if cache is not None and result.get("ok"):
        cache.set(key, result)
    return result
