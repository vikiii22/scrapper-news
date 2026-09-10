"""
Quiniela (LAE): pegar el HTML del boleto y obtener pronósticos.

Flujo:
  1. El usuario copia el HTML de la página del boleto de LAE
     (jornada con % Jugados / % LAE / % Probables por partido).
  2. `parse_quiniela_html()` extrae jornada, equipos, horarios y
     porcentajes oficiales.
  3. `analyze_quiniela()` cruza cada partido con nuestro modelo
     (datos en vivo) y calcula el "valor" (modelo − LAE) por signo.
  4. Todo se guarda en data/db/quiniela.json como BBDD histórica.

El pleno al 15 se trata aparte (signos 0/1/2/M = goles de cada equipo)
y se sugiere con las marginales de Poisson del propio pronóstico.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup

# Nombres cortos del boleto LAE -> nombre usado por nuestro sistema.
TEAM_ALIASES = {
    "ATH.CLUB": "Athletic Bilbao",
    "ATHLETIC": "Athletic Bilbao",
    "ELCHE": "Elche",
    "LEVANTE": "Levante",
    "BARCELONA": "Barcelona",
    "BARCA": "Barcelona",
    "OSASUNA": "Osasuna",
    "ESPANYOL": "Espanyol",
    "RACING S.": "Racing Santander",
    "RACING": "Racing Santander",
    "ALAVES": "Alaves",
    "R.MADRID": "Real Madrid",
    "RAYO": "Rayo Vallecano",
    "SEVILLA": "Sevilla",
    "VALENCIA": "Valencia",
    "VILLARREAL": "Villarreal",
    "BETIS": "Real Betis",
    "CADIZ": "Cadiz",
    "LAS PALMAS": "Las Palmas",
    "TENERIFE": "Tenerife",
    "LEGANES": "Leganes",
    "VALLADOLID": "Real Valladolid",
    "R.OVIEDO": "Real Oviedo",
    "OVIEDO": "Real Oviedo",
    "R.SOCIEDAD": "Real Sociedad",
    "AT.MADRID": "Atletico Madrid",
    "ATLETICO": "Atletico Madrid",
    "GIRONA": "Girona",
    "GETAFE": "Getafe",
    "CELTA": "Celta Vigo",
    "MALLORCA": "Mallorca",
    "ALMERIA": "Almeria",
    "GRANADA": "Granada",
    "EIBAR": "Eibar",
    "ZARAGOZA": "Real Zaragoza",
    "SPORTING": "Sporting Gijon",
    "GIJON": "Sporting Gijon",
}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return " ".join(s.upper().split()).replace(".", "")


_NORM_ALIASES = {_norm(k): v for k, v in TEAM_ALIASES.items()}


def resolve_team(short_name: str) -> str:
    """'R.MADRID (F)' -> 'Real Madrid'. Sin match: nombre limpio tal cual."""
    clean = short_name.replace("(F)", "").strip()
    hit = _NORM_ALIASES.get(_norm(clean))
    if hit:
        return hit
    # fallback: quitar puntos y capitalizar
    return clean.replace(".", "").strip().title()


def _num(text: str) -> Optional[float]:
    try:
        return float(text.strip().replace(",", "."))
    except (ValueError, AttributeError):
        return None


def parse_quiniela_html(html: str) -> Dict[str, Any]:
    """
    Extrae la jornada del HTML del boleto LAE.
    Devuelve {'jornada': int|None, 'matches': [...]}.
    Cada partido: {n, home, away, day, hour, columns, lae, probables,
                   is_pleno, pleno, is_women}.
    Nunca lanza excepción (devuelve lista vacía si no reconoce nada).
    """
    matches: List[Dict[str, Any]] = []
    jornada: Optional[int] = None
    try:
        soup = BeautifulSoup(html, "lxml")

        h3 = soup.find(lambda t: t.name in ("h1", "h2", "h3")
                       and t.get_text() and "JORNADA" in t.get_text().upper())
        if h3:
            m = re.search(r"JORNADA\s*(\d+)", h3.get_text().upper())
            if m:
                jornada = int(m.group(1))

        for box in soup.select("div.c-caja_base__partido"):
            eq = box.select_one("p.c-equipos")
            if not eq:
                continue
            title = (eq.get("title") or eq.get_text(separator=" ", strip=True)).strip()
            if " - " not in title and "\n" not in title:
                continue
            parts = [p.strip() for p in re.split(r"\s*-\s*|\n", title) if p.strip()]
            if len(parts) < 2:
                continue
            home_raw, away_raw = parts[0], parts[1]

            num_el = box.select_one("span.c-equipos__number")
            try:
                n = int(num_el.get_text(strip=True)) if num_el else len(matches) + 1
            except ValueError:
                n = len(matches) + 1

            day_el = box.select_one(".c-marcador-horario__time__day")
            hour_el = box.select_one(".c-marcador-horario__time__hour")
            day = day_el.get_text(strip=True) if day_el else ""
            hour = hour_el.get_text(strip=True) if hour_el else ""

            is_pleno = "m-pleno15" in (box.get("class") or [])

            columns: List[List[float]] = []
            pleno_rows: List[List[float]] = []
            for pct in box.find_all("app-boleto-multiples-porcentajes"):
                for row in pct.select("div[class*='boleto-multiples-porcentajes__row']"):
                    vals = [_num(s.get_text()) for s in row.select("span")]
                    vals = [v for v in vals if v is not None]
                    if len(vals) == 3:
                        columns.append(vals)
                    elif len(vals) == 4:
                        pleno_rows.append(vals)

            lae = columns[1] if len(columns) >= 2 else (columns[0] if columns else None)
            probables = columns[2] if len(columns) >= 3 else None

            matches.append({
                "n": n,
                "home": resolve_team(home_raw),
                "away": resolve_team(away_raw),
                "home_raw": home_raw,
                "away_raw": away_raw,
                "day": day,
                "hour": hour,
                "columns": columns,
                "lae": {"1": lae[0], "X": lae[1], "2": lae[2]} if lae else None,
                "probables": ({"1": probables[0], "X": probables[1], "2": probables[2]}
                              if probables else None),
                "is_pleno": is_pleno,
                "pleno": pleno_rows or None,
                "is_women": "(F)" in home_raw or "(F)" in away_raw,
            })

        matches.sort(key=lambda m: m["n"])
    except Exception:
        pass
    return {"jornada": jornada, "matches": matches}


def pleno_suggestion(lam_home: float, lam_away: float) -> Dict[str, str]:
    """Sugiere el pleno (0/1/2/M) con las marginales de Poisson."""
    try:
        from .prediction_engine import poisson_pmf
    except ImportError:
        from prediction_engine import poisson_pmf

    def pick(lam: float) -> str:
        probs = [poisson_pmf(lam, k) for k in (0, 1, 2)]
        probs.append(max(0.0, 1.0 - sum(probs)))  # M = 3+
        labels = ["0", "1", "2", "M"]
        return labels[probs.index(max(probs))]

    return {"home": pick(lam_home), "away": pick(lam_away)}


def analyze_quiniela(parsed: Dict[str, Any], competition_default: str = "La Liga",
                     live: bool = True, refresh: bool = False,
                     progress_cb=None) -> List[Dict[str, Any]]:
    """
    Calcula el pronóstico de cada partido con nuestro modelo y el valor
    frente a los % LAE. Devuelve lista de dicts listos para guardar/mostrar.
    progress_cb(i, total) se llama tras cada partido (para la UI).
    """
    try:
        from .orchestrator import predict
    except ImportError:
        from orchestrator import predict

    out: List[Dict[str, Any]] = []
    matches = parsed.get("matches", [])
    for i, m in enumerate(matches):
        entry: Dict[str, Any] = dict(m)
        comp = "Liga F" if m.get("is_women") else competition_default
        try:
            r = predict(m["home"], m["away"], comp, live=live, refresh=refresh)
        except Exception as e:
            entry["error"] = str(e)
            out.append(entry)
            if progress_cb:
                progress_cb(i + 1, len(matches))
            continue
        p = r["prob_1x2"]
        entry["modelo"] = {"1": round(p["home"] * 100, 1),
                           "X": round(p["draw"] * 100, 1),
                           "2": round(p["away"] * 100, 1)}
        entry["pick"] = r["prediction_1x2"]
        entry["expected_goals"] = r["expected_goals"]
        entry["data_sources"] = r.get("data_sources")
        if m.get("lae"):
            entry["valor"] = {s: round(entry["modelo"][s] - m["lae"][s], 1)
                              for s in ("1", "X", "2")}
            # mejor valor: signo con mayor diferencia modelo-LAE (mínimo +3)
            best = max(entry["valor"], key=lambda s: entry["valor"][s])
            entry["value_pick"] = best if entry["valor"][best] >= 3 else None
        if m.get("is_pleno"):
            entry["pleno_sugerido"] = pleno_suggestion(
                r["expected_goals"]["home"], r["expected_goals"]["away"])
        out.append(entry)
        if progress_cb:
            progress_cb(i + 1, len(matches))
    return out
