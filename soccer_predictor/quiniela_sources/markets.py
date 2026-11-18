"""Polymarket / Kalshi: contexto de mercados de campeón, nunca por partido."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from .cache import Cache
from .http import get_text

POLY_URL = "https://gamma-api.polymarket.com/events"
KALSHI_URL = "https://api.elections.kalshi.com/trade-api/v2/events"
TITLE_HINTS = ("la liga", "premier league", "serie a", "bundesliga", "ligue 1")


def _get_text(url: str, params: Optional[Dict[str, Any]] = None,
              timeout: int = 8) -> str:
    return get_text(url, params=params, timeout=timeout)


def _polymarket(cache: Optional[Cache]) -> List[Dict[str, Any]]:
    try:
        payload = json.loads(_get_text(POLY_URL, params={"limit": 50, "closed": "false"}))
    except Exception:
        return []

    markets: List[Dict[str, Any]] = []
    for event in payload if isinstance(payload, list) else []:
        title = (event.get("title") or "").strip()
        if not any(hint in title.lower() for hint in TITLE_HINTS):
            continue
        for market in event.get("markets") or []:
            outcomes = market.get("outcomes")
            prices = market.get("outcomePrices")
            try:
                outcomes = json.loads(outcomes) if isinstance(outcomes, str) else outcomes
                prices = json.loads(prices) if isinstance(prices, str) else prices
            except (TypeError, ValueError):
                continue
            if not outcomes or not prices:
                continue
            for name, price in zip(outcomes, prices):
                try:
                    probability = round(float(price) * 100, 1)
                except (TypeError, ValueError):
                    continue
                markets.append({
                    "source": "polymarket",
                    "question": f"{title}: {name}",
                    "probability": probability,
                })
    return markets


def _kalshi(cache: Optional[Cache]) -> List[Dict[str, Any]]:
    try:
        payload = json.loads(_get_text(KALSHI_URL, params={"limit": 50}))
    except Exception:
        return []
    events = payload.get("events") if isinstance(payload, dict) else None
    markets: List[Dict[str, Any]] = []
    for event in events or []:
        title = (event.get("title") or "").strip()
        if not any(hint in title.lower() for hint in TITLE_HINTS):
            continue
        markets.append({"source": "kalshi", "question": title,
                        "probability": None})
    return markets


def outright_context(cache: Optional[Cache] = None) -> Dict[str, Any]:
    key = "markets_outrights"
    if cache is not None:
        cached = cache.get(key)
        if cached:
            return cached

    markets = _polymarket(cache) + _kalshi(cache)
    result = {"ok": bool(markets), "markets": markets,
              "error": None if markets else "sin mercados de liga"}
    if cache is not None:
        cache.set(key, result)
    return result
