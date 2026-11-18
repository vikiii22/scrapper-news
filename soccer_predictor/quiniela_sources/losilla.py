"""Fuente de la jornada: CSV de porcentajes + HTML del boleto de Losilla.

El CSV (`analisisSigno`) trae cuatro secciones: `tecnicos`, `quinielista`,
`lae` y `real`. Mapeo usado en el informe:

    % Jugados  -> quinielista
    % LAE      -> lae   (si aún no está publicado, None)
    % Probables-> real  (probabilidad implícita de las cuotas)
    % Técnicos -> tecnicos
"""

from __future__ import annotations

import csv
import re
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

import requests

try:
    from ..quiniela import parse_quiniela_html, resolve_team
except ImportError:  # pragma: no cover - ejecución directa
    from quiniela import parse_quiniela_html, resolve_team

from .cache import Cache

BASE_URL = "https://www.eduardolosilla.es/"
CSV_URL = "https://api.eduardolosilla.es/analisisSigno"
HEADERS = {"User-Agent": "Mozilla/5.0"}
SECTIONS = ("tecnicos", "quinielista", "lae", "real")
PLENO_KEYS = ("0", "1", "2", "M")


def _num(value: Any) -> Optional[float]:
    try:
        text = str(value).strip().replace(",", ".")
        if not text:
            return None
        return float(text)
    except (TypeError, ValueError):
        return None


def _get_text(url: str, params: Optional[Dict[str, Any]] = None,
              timeout: int = 20) -> str:
    """Descarga y decodifica. UTF-8 primero; latin-1 como respaldo."""
    response = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
    response.raise_for_status()
    try:
        return response.content.decode("utf-8")
    except UnicodeDecodeError:
        return response.content.decode("latin-1")


def _season_number(today: Optional[date] = None) -> int:
    today = today or date.today()
    return today.year + 1 if today.month >= 7 else today.year


def _pct(values: List[Any], keys=("1", "X", "2")) -> Optional[Dict[str, float]]:
    parsed = []
    for raw in values:
        value = _num(raw)
        if value is None:
            return None
        parsed.append(value)
    return dict(zip(keys, parsed))


def _split_teams(raw: str) -> tuple[str, str]:
    if not raw:
        return "", ""
    if " - " in raw:
        home, away = raw.split(" - ", 1)
        return home.strip(), away.strip()
    if "-" in raw:
        home, away = raw.split("-", 1)
        return home.strip(), away.strip()
    return raw.strip(), ""


def parse_csv(text: str) -> Dict[str, List[Dict[str, Any]]]:
    """Parsea el CSV de Losilla y devuelve una lista de 15 por sección."""
    if isinstance(text, bytes):
        try:
            text = text.decode("utf-8")
        except UnicodeDecodeError:
            text = text.decode("latin-1")

    out: Dict[str, List[Dict[str, Any]]] = {name: [] for name in SECTIONS}
    current: Optional[str] = None

    for row in csv.reader(text.splitlines(), delimiter=";"):
        if not row:
            continue
        first = (row[0] or "").strip()
        joined = ";".join(row).strip().lower()
        if joined in SECTIONS:
            current = joined
            continue
        if current is None or first.lower().startswith("n"):
            continue

        n_raw = first
        teams_raw = (row[1] if len(row) > 1 else "").strip()
        if not n_raw:
            continue
        n = _num(n_raw)
        if n is None:
            continue
        n = int(n)

        base = (row[2] if len(row) > 2 else "").strip()
        probable = (row[3] if len(row) > 3 else "").strip()
        posible = (row[4] if len(row) > 4 else "").strip()
        dificil = (row[5] if len(row) > 5 else "").strip()
        bomba = (row[6] if len(row) > 6 else "").strip()
        values = row[7:]

        home_raw, away_raw = _split_teams(teams_raw)
        entry: Dict[str, Any] = {
            "n": n,
            "equipos_raw": teams_raw,
            "home_raw": home_raw,
            "away_raw": away_raw,
            "base": base,
            "probable": probable,
            "posible": posible,
            "dificil": dificil,
            "bomba": bomba,
            "percentages": _pct(values[:3]),
            "lae": None,
            "pleno": None,
        }
        if current == "lae" and entry["percentages"]:
            entry["lae"] = entry["percentages"]

        if n == 15:
            home_dist = _pct(values[:4], PLENO_KEYS)
            entry["percentages"] = home_dist
            # La fila siguiente (número vacío) es el equipo visitante del pleno.
            entry["_needs_away"] = True
            out[current].append(entry)
            continue

        out[current].append(entry)

    # Segunda pasada para el pleno: emparejar fila 15 (local) con la siguiente.
    for name in SECTIONS:
        rows = out[name]
        pleno_idx = next((i for i, r in enumerate(rows) if r["n"] == 15), None)
        if pleno_idx is None:
            continue
        # Necesitamos la fila cruda del visitante; se reconstruye desde el texto.
        away = _find_pleno_away(text, name)
        if away is None:
            rows[pleno_idx]["pleno"] = None
            rows[pleno_idx].pop("_needs_away", None)
            continue
        rows[pleno_idx]["pleno"] = {
            "home": rows[pleno_idx].get("percentages"),
            "away": away["percentages"],
        }
        rows[pleno_idx]["away_raw"] = away["away_raw"]
        rows[pleno_idx].pop("_needs_away", None)

    for name in SECTIONS:
        for row in out[name]:
            row.pop("_needs_away", None)
    return out


def _find_pleno_away(text: str, section: str) -> Optional[Dict[str, Any]]:
    """Busca la fila del visitante del pleno dentro de una sección."""
    if isinstance(text, bytes):
        text = text.decode("utf-8", errors="replace")
    current = None
    for row in csv.reader(text.splitlines(), delimiter=";"):
        if not row:
            continue
        joined = ";".join(row).strip().lower()
        if joined in SECTIONS:
            current = joined
            continue
        if current != section or len(row) < 2:
            continue
        if (row[0] or "").strip():
            continue
        team = (row[1] or "").strip()
        if not team:
            continue
        values = row[7:]
        dist = _pct(values[:4], PLENO_KEYS)
        if dist:
            return {"away_raw": team, "percentages": dist}
    return None


def _close_from_html(html: str) -> str:
    match = re.search(
        r"CIERRE\s+([A-ZÁÉÍÓÚÑ]+)\s+(\d{1,2}/\d{1,2})", html or "", re.IGNORECASE
    )
    if not match:
        return ""
    return f"{match.group(1).upper()} {match.group(2)}"


def parse_boleto(html: str) -> Dict[str, Any]:
    parsed = parse_quiniela_html(html)
    return {
        "jornada": parsed.get("jornada"),
        "close": _close_from_html(html),
        "matches": parsed.get("matches", []),
    }


def fetch_jornada(jornada: Optional[int] = None, html: Optional[str] = None,
                  cache: Optional[Cache] = None, timeout: int = 20) -> Dict[str, Any]:
    """Jornada vigente (o la pedida) mezclando CSV y HTML del boleto."""
    season = _season_number()

    if jornada is not None and cache is not None:
        cached = cache.get(f"losilla_{jornada}_{season}")
        if cached:
            return cached

    page = html if html is not None else _get_text(BASE_URL, timeout=timeout)
    boleto = parse_boleto(page)
    if jornada is None:
        jornada = boleto.get("jornada")
    if not jornada:
        raise ValueError("No se pudo leer la jornada")

    csv_text = _get_text(
        CSV_URL,
        params={"num_jornada": jornada, "num_temporada": season, "csv": "true"},
        timeout=timeout,
    )
    sections = parse_csv(csv_text)
    real = {row["n"]: row for row in sections.get("real", [])}
    quinielista = {row["n"]: row for row in sections.get("quinielista", [])}
    lae_rows = {row["n"]: row for row in sections.get("lae", [])}
    tecnicos = {row["n"]: row for row in sections.get("tecnicos", [])}

    if len(real) != 15 and html is None:
        raise ValueError("No se pudo leer la jornada")

    matches: List[Dict[str, Any]] = []
    html_by_n = {m["n"]: m for m in boleto.get("matches", [])}
    for n in range(1, 16):
        hm = html_by_n.get(n, {})
        home_raw = hm.get("home_raw") or (
            real.get(n, {}).get("home_raw") or ""
        )
        away_raw = hm.get("away_raw") or (
            real.get(n, {}).get("away_raw") or ""
        )
        is_women = bool(hm.get("is_women")) or "(F)" in f"{home_raw}{away_raw}"
        is_pleno = n == 15 or bool(hm.get("is_pleno"))

        def section_pct(rows, key="percentages"):
            row = rows.get(n) or {}
            value = row.get(key)
            return dict(value) if value else None

        percentages = {
            "jugados": None if is_pleno else section_pct(quinielista),
            "lae": None if is_pleno else section_pct(lae_rows),
            "probables": None if is_pleno else section_pct(real),
            "tecnicos": None if is_pleno else section_pct(tecnicos),
        }
        pleno = None
        if is_pleno:
            pleno = (real.get(15) or {}).get("pleno") or (
                (tecnicos.get(15) or {}).get("pleno")
            )

        matches.append({
            "n": n,
            "home": resolve_team(home_raw),
            "away": resolve_team(away_raw),
            "home_raw": home_raw,
            "away_raw": away_raw,
            "day": hm.get("day", ""),
            "hour": hm.get("hour", ""),
            "is_women": is_women,
            "is_pleno": is_pleno,
            "percentages": percentages,
            "lae": percentages["lae"],
            "probables": percentages["probables"],
            "pleno": pleno,
        })

    result = {
        "jornada": int(jornada),
        "season": season,
        "close": boleto.get("close", ""),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "matches": matches,
    }
    if cache is not None:
        cache.set(f"losilla_{jornada}_{season}", result)
    return result
