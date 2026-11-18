"""Football-Data.co.uk: forma reciente, xG y cuotas de cierre."""

from __future__ import annotations

import csv
import io
from datetime import date, datetime
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional
from unicodedata import normalize

from .cache import Cache
from .http import get_text

BASE_URL = "https://www.football-data.co.uk/mmz4281"
LEAGUES = {"SP1", "SP2"}
ODDS_TRIPLETS = (("B365H", "B365D", "B365A"),
                 ("PSCH", "PSD", "PSA"),
                 ("BFDH", "BFDD", "BFDA"),
                 ("AvgH", "AvgD", "AvgA"),
                 ("BWH", "BWD", "BWA"))


def _get_text(url: str, timeout: int = 20) -> str:
    return get_text(url, timeout=timeout)


def _norm(value: str) -> str:
    text = normalize("NFKD", value or "").encode("ascii", "ignore").decode()
    return " ".join(text.lower().split())


# Football-Data usa nombres cortos; el resto del proyecto, los largos.
FD_ALIASES = {
    "athletic bilbao": "ath bilbao",
    "atletico madrid": "ath madrid",
    "real betis": "betis",
    "real sociedad": "sociedad",
    "celta vigo": "celta",
    "deportivo": "la coruna",
    "racing santander": "santander",
    "rayo vallecano": "vallecano",
    "espanyol": "espanol",
    "sporting gijon": "sp gijon",
    "real oviedo": "oviedo",
    "real valladolid": "valladolid",
    "real zaragoza": "zaragoza",
}


def _alias(name: str) -> str:
    normalized = _norm(name)
    return FD_ALIASES.get(normalized, normalized)


def _same(a: str, b: str, threshold: float = 0.72) -> bool:
    na, nb = _alias(a), _alias(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    return SequenceMatcher(None, na, nb).ratio() >= threshold


def _season_code(today: Optional[date] = None) -> str:
    today = today or date.today()
    start = today.year if today.month >= 7 else today.year - 1
    return f"{start % 100:02d}{(start + 1) % 100:02d}"


def _to_number(value: str) -> Any:
    text = (value or "").strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        return text


def parse_csv(text: str) -> List[Dict[str, Any]]:
    reader = csv.DictReader(io.StringIO(text))
    rows: List[Dict[str, Any]] = []
    for raw in reader:
        if not raw.get("HomeTeam") or not raw.get("AwayTeam"):
            continue
        row: Dict[str, Any] = {}
        for key, value in raw.items():
            if key is None:
                continue
            row[key] = _to_number(value)
        rows.append(row)
    return rows


def load_league(code: str, cache: Optional[Cache] = None,
                timeout: int = 20) -> Dict[str, Any]:
    code = (code or "").upper()
    url = f"{BASE_URL}/{_season_code()}/{code}.csv"
    if code not in LEAGUES:
        return {"ok": False, "rows": [], "error": f"liga no soportada: {code}",
                "source_url": url}

    key = f"football_data_{code}_{_season_code()}"
    if cache is not None:
        cached = cache.get(key)
        if cached and cached.get("ok"):
            return cached

    try:
        text = _get_text(url, timeout=timeout)
        rows = parse_csv(text)
        result = {"ok": bool(rows), "rows": rows, "error": None,
                  "source_url": url}
    except Exception as exc:  # red, 403, CSV roto...
        result = {"ok": False, "rows": [], "error": str(exc),
                  "source_url": url}

    if cache is not None and result.get("ok"):
        cache.set(key, result)
    return result


def _row_date(row: Dict[str, Any]) -> datetime:
    raw = row.get("Date")
    if isinstance(raw, str):
        for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
            try:
                return datetime.strptime(raw, fmt)
            except ValueError:
                continue
    return datetime.min


def team_form(rows: List[Dict[str, Any]], team: str, n: int = 5,
              venue: Optional[str] = None) -> Dict[str, Any]:
    played: List[Dict[str, Any]] = []
    for row in rows:
        home = row.get("HomeTeam") or ""
        away = row.get("AwayTeam") or ""
        if _same(team, home):
            is_home = True
        elif _same(team, away):
            is_home = False
        else:
            continue
        if venue == "home" and not is_home:
            continue
        if venue == "away" and is_home:
            continue

        gf = row.get("FTHG") if is_home else row.get("FTAG")
        ga = row.get("FTAG") if is_home else row.get("FTHG")
        if gf is None or ga is None:
            continue
        xg = row.get("HxG") if is_home else row.get("AxG")
        xga = row.get("AxG") if is_home else row.get("HxG")
        result = "W" if gf > ga else ("D" if gf == ga else "L")
        played.append({
            "date": row.get("Date"),
            "opponent": away if is_home else home,
            "home": is_home,
            "gf": int(gf),
            "ga": int(ga),
            "result": result,
            "xg": float(xg) if isinstance(xg, (int, float)) else None,
            "xga": float(xga) if isinstance(xga, (int, float)) else None,
        })

    played.sort(key=lambda item: _row_date({"Date": item["date"]}))
    matches = played[-n:]
    points = sum(3 if m["result"] == "W" else (1 if m["result"] == "D" else 0)
                 for m in matches)
    xg_values = [m["xg"] for m in matches if m["xg"] is not None]
    xga_values = [m["xga"] for m in matches if m["xga"] is not None]
    return {
        "recent": "".join(m["result"] for m in matches),
        "gf": sum(m["gf"] for m in matches),
        "ga": sum(m["ga"] for m in matches),
        "xg": round(sum(xg_values), 2) if xg_values else None,
        "xga": round(sum(xga_values), 2) if xga_values else None,
        "ppg": round(points / len(matches), 2) if matches else 0.0,
        "matches": matches,
    }


def closing_odds(rows: List[Dict[str, Any]], home: str,
                 away: str) -> Optional[Dict[str, float]]:
    for row in reversed(rows):
        if not (_same(home, row.get("HomeTeam") or "")
                and _same(away, row.get("AwayTeam") or "")):
            continue
        for h_key, d_key, a_key in ODDS_TRIPLETS:
            values = [row.get(h_key), row.get(d_key), row.get(a_key)]
            if not all(isinstance(v, (int, float)) and v > 1 for v in values):
                continue
            implied = [100.0 / float(v) for v in values]
            total = sum(implied)
            if total <= 0:
                continue
            return {"1": round(implied[0] / total * 100, 1),
                    "X": round(implied[1] / total * 100, 1),
                    "2": round(implied[2] / total * 100, 1)}
    return None
