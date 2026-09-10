"""
Módulo de obtención de datos para el predictor de fútbol.

Este módulo permite obtener datos básicos sobre equipos de fútbol
usando fuentes GRATUITAS:

1. API-Football (tier free - requiere API key gratuita)
2. Football-Data.org (tier free - requiere token gratuito)
3. Datos estáticos / CSV de ejemplo (funciona sin API key)

El diseño es modular: si no tienes API key, el sistema automáticamente
usa los datos estáticos de ejemplo incluidos en la carpeta `data/`.
"""

import os
import csv
import json
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Cargamos variables de entorno si existe un archivo .env en la raíz del proyecto
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # python-dotenv es opcional, si no está instalado seguimos sin .env

import requests

# ---------------------------------------------------------------------------
# Configuración general
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent  # raíz del proyecto
DATA_DIR = BASE_DIR / "data"

# Claves de API (opcionales). Se pueden configurar vía .env o variables de entorno
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY", "")
FOOTBALL_DATA_TOKEN = os.getenv("FOOTBALL_DATA_TOKEN", "")

# Definimos el encabezado de User-Agent para evitar bloqueos en scraping simple
HEADERS = {"User-Agent": "Mozilla/5.0 (scrapper-news soccer-predictor)"}


# ===========================================================================
# 1. DATOS ESTÁTICOS / CSV (fallback - siempre disponible, sin API)
# ===========================================================================

# Datos de ejemplo de equipos: forma reciente (últimos 5 partidos), goles, etc.
# Formato: "team_name": {"goals_for": X, "goals_against": Y, "recent": "WDLWL", ...}
# 'recent' usa: W = victoria, D = empate, L = derrota (último partido = último char)

DEFAULT_TEAMS = {
    "Real Madrid": {
        "goals_for": 42,
        "goals_against": 14,
        "recent": "WWWDW",
        "position": 1,
    },
    "Barcelona": {
        "goals_for": 40,
        "goals_against": 16,
        "recent": "WWWWD",
        "position": 2,
    },
    "Atletico Madrid": {
        "goals_for": 34,
        "goals_against": 15,
        "recent": "DWWWD",
        "position": 3,
    },
    "Manchester City": {
        "goals_for": 45,
        "goals_against": 13,
        "recent": "WWDWW",
        "position": 1,
    },
    "Arsenal": {
        "goals_for": 38,
        "goals_against": 17,
        "recent": "WWLDW",
        "position": 2,
    },
    "Liverpool": {
        "goals_for": 42,
        "goals_against": 19,
        "recent": "WDWWW",
        "position": 3,
    },
    "Chelsea": {
        "goals_for": 31,
        "goals_against": 22,
        "recent": "DWDLL",
        "position": 8,
    },
    "Manchester United": {
        "goals_for": 27,
        "goals_against": 25,
        "recent": "LDLWW",
        "position": 6,
    },
    "Paris Saint Germain": {
        "goals_for": 44,
        "goals_against": 15,
        "recent": "WWWWD",
        "position": 1,
    },
    "Bayern Munich": {
        "goals_for": 50,
        "goals_against": 12,
        "recent": "WWWWW",
        "position": 1,
    },
    "Borussia Dortmund": {
        "goals_for": 36,
        "goals_against": 24,
        "recent": "WDLWW",
        "position": 4,
    },
    "Inter Milan": {
        "goals_for": 39,
        "goals_against": 12,
        "recent": "WWWDL",
        "position": 1,
    },
    "Milan": {
        "goals_for": 33,
        "goals_against": 20,
        "recent": "DWWLW",
        "position": 3,
    },
    "Juventus": {
        "goals_for": 28,
        "goals_against": 16,
        "recent": "WDWDL",
        "position": 2,
    },
    "Napoli": {
        "goals_for": 35,
        "goals_against": 18,
        "recent": "LWDWW",
        "position": 4,
    },
    "Tottenham": {
        "goals_for": 32,
        "goals_against": 21,
        "recent": "WLLWD",
        "position": 5,
    },
}

# Equipos adicionales de ligas españolas (La Liga + Segunda División)
# Datos orientativos (estimaciones para la temporada 2026-27).
# Añadir aquí más equipos es la forma más fácil de ampliar sin API.
SPANISH_TEAMS = {
    "Levante": {
        "goals_for": 22,
        "goals_against": 14,
        "recent": "WDLWD",
        "position": 5,
    },
    "Elche": {
        "goals_for": 20,
        "goals_against": 14,
        "recent": "DWLWD",
        "position": 6,
    },
    "Sporting Gijon": {
        "goals_for": 21,
        "goals_against": 16,
        "recent": "WLDWD",
        "position": 8,
    },
    "Racing Santander": {
        "goals_for": 24,
        "goals_against": 15,
        "recent": "WWDWL",
        "position": 3,
    },
    "Real Oviedo": {
        "goals_for": 19,
        "goals_against": 13,
        "recent": "DWLWD",
        "position": 7,
    },
    "Granada": {
        "goals_for": 18,
        "goals_against": 17,
        "recent": "LDWWD",
        "position": 12,
    },
    "Tenerife": {
        "goals_for": 17,
        "goals_against": 16,
        "recent": "WLWDW",
        "position": 10,
    },
    "Almeria": {
        "goals_for": 23,
        "goals_against": 18,
        "recent": "WWDWL",
        "position": 4,
    },
    "Eibar": {
        "goals_for": 18,
        "goals_against": 14,
        "recent": "DWDWW",
        "position": 9,
    },
    "Real Zaragoza": {
        "goals_for": 20,
        "goals_against": 17,
        "recent": "WDWDL",
        "position": 10,
    },
    "Cadiz": {
        "goals_for": 16,
        "goals_against": 15,
        "recent": "LWDWD",
        "position": 11,
    },
    "Real Betis": {
        "goals_for": 28,
        "goals_against": 19,
        "recent": "WDDWW",
        "position": 6,
    },
    "Real Sociedad": {
        "goals_for": 30,
        "goals_against": 18,
        "recent": "WWDWD",
        "position": 5,
    },
    "Athletic Bilbao": {
        "goals_for": 29,
        "goals_against": 17,
        "recent": "WWDWW",
        "position": 4,
    },
    "Valencia": {
        "goals_for": 24,
        "goals_against": 20,
        "recent": "WDWDL",
        "position": 8,
    },
    "Sevilla": {
        "goals_for": 25,
        "goals_against": 21,
        "recent": "WDDWL",
        "position": 9,
    },
    "Villarreal": {
        "goals_for": 33,
        "goals_against": 20,
        "recent": "WWWDD",
        "position": 4,
    },
    "Real Valladolid": {
        "goals_for": 17,
        "goals_against": 20,
        "recent": "LDDLW",
        "position": 16,
    },
    "Osasuna": {
        "goals_for": 21,
        "goals_against": 22,
        "recent": "DDWLD",
        "position": 13,
    },
    "Girona": {
        "goals_for": 26,
        "goals_against": 24,
        "recent": "DWWLD",
        "position": 11,
    },
    "Espanyol": {
        "goals_for": 18,
        "goals_against": 22,
        "recent": "LDLWD",
        "position": 15,
    },
    "Celta Vigo": {
        "goals_for": 23,
        "goals_against": 22,
        "recent": "WDLWD",
        "position": 12,
    },
    "Mallorca": {
        "goals_for": 19,
        "goals_against": 19,
        "recent": "DDWLD",
        "position": 14,
    },
    "Getafe": {
        "goals_for": 16,
        "goals_against": 18,
        "recent": "LWDWD",
        "position": 15,
    },
    "Rayo Vallecano": {
        "goals_for": 22,
        "goals_against": 21,
        "recent": "WDWDL",
        "position": 10,
    },
    "Las Palmas": {
        "goals_for": 20,
        "goals_against": 21,
        "recent": "LWDDW",
        "position": 12,
    },
    "Alaves": {
        "goals_for": 18,
        "goals_against": 19,
        "recent": "DWDWL",
        "position": 13,
    },
    "Leganes": {
        "goals_for": 17,
        "goals_against": 19,
        "recent": "LWDWD",
        "position": 14,
    },
}

# Unimos los diccionarios para tener una única base de equipos
for _k, _v in SPANISH_TEAMS.items():
    DEFAULT_TEAMS.setdefault(_k, _v)

# Cabecera de la tabla H2H (head-to-head - enfrentamientos directos) de ejemplo
# Cada fila: [equipo_local, equipo_visitante, goles_local, goles_visitante, competicion]
DEFAULT_H2H = [
    ["Real Madrid", "Barcelona", 3, 2, "La Liga"],
    ["Barcelona", "Real Madrid", 1, 2, "La Liga"],
    ["Real Madrid", "Barcelona", 0, 1, "Copa del Rey"],
    ["Real Madrid", "Barcelona", 2, 1, "Supercopa"],
    ["Barcelona", "Real Madrid", 4, 0, "La Liga"],
    ["Manchester City", "Arsenal", 2, 0, "Premier League"],
    ["Arsenal", "Manchester City", 1, 3, "Premier League"],
    ["Manchester City", "Arsenal", 2, 2, "Premier League"],
    ["Arsenal", "Manchester City", 1, 0, "FA Cup"],
    ["Liverpool", "Manchester City", 1, 1, "Premier League"],
    ["Manchester City", "Liverpool", 2, 1, "Premier League"],
    ["Liverpool", "Manchester City", 3, 1, "Premier League"],
    ["Manchester City", "Liverpool", 2, 2, "Premier League"],
    ["Liverpool", "Chelsea", 4, 1, "Premier League"],
    ["Chelsea", "Liverpool", 1, 2, "Premier League"],
    ["Manchester United", "Liverpool", 0, 0, "Premier League"],
    ["Liverpool", "Manchester United", 2, 1, "Premier League"],
    ["Paris Saint Germain", "Marseille", 3, 0, "Ligue 1"],
    ["Marseille", "Paris Saint Germain", 0, 2, "Ligue 1"],
    ["Bayern Munich", "Borussia Dortmund", 4, 0, "Bundesliga"],
    ["Borussia Dortmund", "Bayern Munich", 1, 2, "Bundesliga"],
    ["Borussia Dortmund", "Bayern Munich", 2, 3, "Supercup"],
    ["Inter Milan", "Milan", 2, 0, "Serie A"],
    ["Milan", "Inter Milan", 1, 2, "Serie A"],
    ["Milan", "Inter Milan", 1, 1, "Coppa Italia"],
    ["Inter Milan", "Milan", 3, 0, "Supercoppa"],
    ["Juventus", "Inter Milan", 0, 2, "Serie A"],
    ["Inter Milan", "Juventus", 1, 1, "Serie A"],
    ["Juventus", "Napoli", 2, 1, "Serie A"],
    ["Napoli", "Juventus", 2, 2, "Serie A"],
]


def _load_static_csv(filename):
    """Carga un CSV desde la carpeta data/ si existe."""
    path = DATA_DIR / filename
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def get_static_team_data(team_name):
    """
    Devuelve los datos básicos de un equipo desde el diccionario estático.
    Si el equipo no está en la tabla, se crean datos genéricos equilibrados
    y se marca `has_data=False` para que la UI no los presente como reales.
    """
    team_normalized = team_name.strip().lower()

    for name, data in DEFAULT_TEAMS.items():
        if name.lower() in team_normalized or team_normalized in name.lower():
            # el equipo existe en nuestra base estática
            return {
                "name": name,
                "goals_for": data["goals_for"],
                "goals_against": data["goals_against"],
                "recent": data["recent"],
                "position": data["position"],
                "source": "static",
                "has_data": True,
            }

    # Equipo desconocido -> datos neutros para que el sistema siga funcionando.
    # IMPORTANTE: marcamos has_data=False para que no presente la forma
    # inventada ("DDDDD") como si fueran resultados reales.
    return {
        "name": team_name,
        "goals_for": 30,
        "goals_against": 30,
        "recent": "",  # sin forma real conocida
        "position": 10,
        "source": "static-fallback",
        "has_data": False,
    }


def get_static_h2h(team_a, team_b, limit=6):
    """
    Devuelve la historia de enfrentamientos directos entre dos equipos
    desde la tabla estática DEFAULT_H2H.
    """
    matches = []
    for row in DEFAULT_H2H:
        home, away = row[0].lower(), row[1].lower()
        a, b = team_a.lower(), team_b.lower()

        # Coincidimos si los equipos aparecen en los nombres
        if (a in home or home in a) and (b in away or away in b):
            matches.append(row)

    # Tomamos los últimos 'limit' enfrentamientos
    return matches[-limit:]


def get_team_goals_per_match(team_name):
    """
    Calcula los goles promedio por partido de un equipo.
    Home advantage approx: sumamos ~0.3 goles al equipo local.
    """
    data = get_static_team_data(team_name)
    return data["goals_for"] / 25.0, data["goals_against"] / 25.0


# ===========================================================================
# 2. API FOOTBALL (requiere API key gratuita - opcional)
# ===========================================================================

def get_team_from_api(team_name):
    """
    Busca un equipo en API-Football. Requiere la key gratuita en
    la variable de entorno API_FOOTBALL_KEY.
    Retorna None si no hay key o si falla la petición.
    """
    if not API_FOOTBALL_KEY:
        return None

    try:
        url = "https://v3.football.api-sports.io/teams"
        params = {"search": team_name}
        headers = {"x-apisports-key": API_FOOTBALL_KEY}
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if data.get("results", 0) > 0:
            team = data["response"][0]["team"]
            # Extraemos solo datos relevantes
            return {
                "api_id": team["id"],
                "name": team["name"],
                "country": team.get("country", ""),
                "logo": team.get("logo", ""),
            }
    except Exception:
        # No queremos que un fallo de API rompa toda la app
        return None

    return None


def get_team_fixtures_from_api(team_id):
    """
    Obtiene los últimos partidos de un equipo desde API-Football.
    Devuelve None si no se puede acceder.
    """
    if not API_FOOTBALL_KEY:
        return None

    try:
        url = "https://v3.football.api-sports.io/fixtures"
        params = {"team": team_id, "last": 10, "status": "FT"}
        headers = {"x-apisports-key": API_FOOTBALL_KEY}
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json().get("response", [])
    except Exception:
        return None


def get_team_form_from_fixtures(fixtures, team_name):
    """
    Calcula la forma reciente (W/D/L) de un equipo a partir de sus
    últimos partidos (formato API-Football).
    """
    if not fixtures:
        return None

    form = []
    for match in fixtures:
        home = match["teams"]["home"]
        away = match["teams"]["away"]

        is_home = team_name.lower() in home["name"].lower() or str(home["id"]) in str(team_name)

        if is_home:
            gf = home["goals"] if home["goals"] is not None else 0
            ga = away["goals"] if away["goals"] is not None else 0
        else:
            gf = away["goals"] if away["goals"] is not None else 0
            ga = home["goals"] if home["goals"] is not None else 0

        if gf > ga:
            form.append("W")
        elif gf == ga:
            form.append("D")
        else:
            form.append("L")

    # Formato 'recent' que usa nuestro motor de predicción (último = más reciente)
    return form  # ya está en orden cronológico


# ===========================================================================
# 3. FOOTBALL-DATA.ORG (requiere token gratuito - opcional)
# ===========================================================================

def get_team_from_football_data(team_name):
    """
    Busca un equipo en Football-Data.org. Requiere token gratuito en
    la variable de entorno FOOTBALL_DATA_TOKEN.
    """
    if not FOOTBALL_DATA_TOKEN:
        return None

    try:
        url = "https://api.football-data.org/v4/teams"
        headers = {"X-Auth-Token": FOOTBALL_DATA_TOKEN}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        for team in data.get("teams", []):
            if team_name.lower() in team["name"].lower():
                return {
                    "id": team["id"],
                    "name": team["name"],
                    "short_name": team.get("shortName", ""),
                }
    except Exception:
        return None

    return None


# ===========================================================================
# 4. SCRAPING LIGERO DE SOFASCORE (opcional, sin API key)
# ===========================================================================

def get_team_form_from_sofascore(team_name):
    """
    Intenta obtener la forma reciente escrapeando SofaScore.
    Es una heurística simple y puede fallar (por eso devolvemos None
    si no funciona, y el sistema usa los datos estáticos como fallback).
    """
    try:
        # SofaScore usa una API pública (sin key) con formato JSON
        url = "https://www.sofascore.com/api/v1/search/all"
        params = {"q": team_name}
        resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        # Buscamos el primer equipo en los resultados
        for item in data.get("results", []):
            if item.get("type") == "team":
                team_id = item["entity"]["id"]
                # Obtenemos los últimos partidos
                fixtures_url = f"https://www.sofascore.com/api/v1/team/{team_id}/events/last/0"
                fixtures_resp = requests.get(fixtures_url, headers=HEADERS, timeout=10)
                if fixtures_resp.ok:
                    events = fixtures_resp.json().get("events", [])
                    form = []
                    for ev in events[:5]:
                        home = ev["homeTeam"]["id"]
                        away = ev["awayTeam"]["id"]
                        home_score = ev.get("homeScore", {}).get("current", 0)
                        away_score = ev.get("awayScore", {}).get("current", 0)
                        if home_score is None or away_score is None:
                            continue
                        if team_id == home:
                            if home_score > away_score:
                                form.append("W")
                            elif home_score == away_score:
                                form.append("D")
                            else:
                                form.append("L")
                        elif team_id == away:
                            if away_score > home_score:
                                form.append("W")
                            elif home_score == away_score:
                                form.append("D")
                            else:
                                form.append("L")
                    if len(form) >= 3:
                        return form
        return None
    except Exception:
        return None


# ===========================================================================
# FUNCIÓN PRINCIPAL DE ORQUESTACIÓN DE DATOS (pipeline live + BBDD JSON)
# ===========================================================================
# Orden:
#   1. Caché local JSON (data/db/teams.json, TTL configurable)
#   2. Búsqueda en vivo sin API key (TheSportsDB + FBref + noticias) -> CUALQUIER equipo
#   3. API-Football / Football-Data (si hay key configurada)
#   4. SofaScore ligero
#   5. Datos estáticos (seed inicial)
# Todo lo obtenido en vivo se guarda en la BBDD JSON automáticamente.

CACHE_TTL_HOURS = float(os.getenv("CACHE_TTL_HOURS", "6"))


def fetch_and_store(team_name, with_news=True):
    """Fuerza búsqueda en vivo y la guarda en la BBDD JSON. Devuelve el record o None."""
    try:
        from .scrapers import live_search as _live
        from . import database as _db
    except ImportError:
        from scrapers import live_search as _live
        import database as _db
    rec = _live.fetch_team_live(team_name, with_news=with_news)
    if rec:
        return _db.save_team(rec)
    return None


def get_team_data(team_name, live=True, with_news=False, refresh=False):
    """
    Obtiene los datos de un equipo, intentando en orden:
    1. Caché JSON (si no está caducada y refresh=False)
    2. Búsqueda en vivo (TheSportsDB/FBref, sin key -> cualquier equipo)
    3. API-Football (si hay key)
    4. SofaScore (scraping ligero, sin key)
    5. Datos estáticos (seed)

    Devuelve un diccionario con las estadísticas del equipo.
    """
    # 1. Caché local
    try:
        from . import database as _db
    except ImportError:
        import database as _db
    if not refresh:
        cached = _db.get_team(team_name, max_age_hours=CACHE_TTL_HOURS)
        if cached:
            cached["source"] = cached.get("source", "") + "+cache" if cached.get("source") else "cache"
            return cached

    # 2. Búsqueda en vivo (cualquier equipo, sin key)
    if live:
        try:
            try:
                from .scrapers import live_search as _live
            except ImportError:
                from scrapers import live_search as _live
            rec = _live.fetch_team_live(team_name, with_news=with_news)
            if rec and rec.get("recent"):
                return _db.save_team(rec)
        except Exception:
            pass

    # 3. Intentamos con API-Football si hay key
    if API_FOOTBALL_KEY:
        team = get_team_from_api(team_name)
        if team:
            fixtures = get_team_fixtures_from_api(team["api_id"])
            form = get_team_form_from_fixtures(fixtures, team["name"])
            if form:
                # Calculamos promedios de goles a partir de fixtures
                gf = sum(
                    (f["teams"]["home"]["goals"] or 0)
                    if team["name"].lower() in f["teams"]["home"]["name"].lower()
                    else (f["teams"]["away"]["goals"] or 0)
                    for f in fixtures
                )
                return {
                    "name": team["name"],
                    "goals_for": gf,
                    "goals_against": 25,  # promedio ~ 2.5 goles por partido
                    "recent": "".join(form),
                    "position": 0,
                    "source": "api-football",
                }

    # 2. Intentamos con SofaScore (scraping ligero)
    form = get_team_form_from_sofascore(team_name)
    if form:
        data = get_static_team_data(team_name)
        data["recent"] = "".join(form)
        data["source"] = "sofascore"
        return data

    # 3. Fallback a datos estáticos
    return get_static_team_data(team_name)


def get_h2h(team_a, team_b, limit=6, live=True):
    """
    Obtiene la historia de enfrentamientos entre dos equipos.
    Orden: caché JSON -> live (TheSportsDB) -> API-Football -> estático.
    Lo encontrado en vivo se guarda en la BBDD.
    """
    try:
        from . import database as _db
    except ImportError:
        import database as _db

    cached = _db.get_h2h(team_a, team_b)
    if cached:
        return cached[-limit:]

    if live:
        try:
            try:
                from .scrapers import live_search as _live
            except ImportError:
                from scrapers import live_search as _live
            found = _live.fetch_h2h_live(team_a, team_b, limit=limit)
            if found:
                _db.save_h2h(team_a, team_b, found, source="thesportsdb-live")
                return found
        except Exception:
            pass

    # Si hay API-Football, intentamos get H2H desde ahí
    if API_FOOTBALL_KEY:
        team_a_api = get_team_from_api(team_a)
        team_b_api = get_team_from_api(team_b)
        if team_a_api and team_b_api:
            try:
                url = "https://v3.football.api-sports.io/fixtures/headtohead"
                params = {
                    "h2h": f"{team_a_api['api_id']}-{team_b_api['api_id']}",
                    "last": limit,
                }
                headers = {"x-apisports-key": API_FOOTBALL_KEY}
                resp = requests.get(url, params=params, headers=headers, timeout=10)
                if resp.ok:
                    responses = resp.json().get("response", [])
                    if responses:
                        h2h = []
                        for match in responses:
                            h2h.append(
                                [
                                    match["teams"]["home"]["name"],
                                    match["teams"]["away"]["name"],
                                    match["goals"]["home"],
                                    match["goals"]["away"],
                                    match.get("league", {}).get("name", ""),
                                ]
                            )
                        return h2h
            except Exception:
                pass

    # H2H live guardado también en caché aunque venga de API
    # Fallback a datos estáticos
    static = get_static_h2h(team_a, team_b, limit)
    if static:
        try:
            _db.save_h2h(team_a, team_b, static, source="static")
        except Exception:
            pass
    return static


def get_available_teams():
    """Equipos de la semilla estática + los ya guardados en la BBDD JSON."""
    names = set(DEFAULT_TEAMS.keys())
    try:
        try:
            from . import database as _db
        except ImportError:
            import database as _db
        for t in _db.list_teams():
            if t.get("name"):
                names.add(t["name"])
    except Exception:
        pass
    return sorted(names)


def get_competitions():
    """Devuelve una lista de competiciones de ejemplo."""
    return [
        "La Liga",
        "Premier League",
        "Serie A",
        "Bundesliga",
        "Ligue 1",
        "Champions League",
        "Europa League",
        "Copa del Rey",
        "FA Cup",
        "Otra",
    ]


def parse_team_input(raw_input):
    """
    Convierte la entrada del usuario en un nombre de equipo estandarizado.
    1. Mira primero la BBDD JSON (equipos ya buscados en vivo).
    2. Luego la semilla estática.
    3. Si no hay match, devuelve el input tal cual -> se buscará en vivo.
    """
    raw = raw_input.strip().lower()
    candidates = list(DEFAULT_TEAMS.keys())
    try:
        try:
            from . import database as _db
        except ImportError:
            import database as _db
        for t in _db.list_teams():
            if t.get("name") and t["name"] not in candidates:
                candidates.append(t["name"])
    except Exception:
        pass

    # 1. Match EXACTO (prioridad máxima)
    for name in candidates:
        if raw == name.lower():
            return name

    # 2. Match por palabra completa (evita que "Milan" coincida con "Inter Milan")
    raw_words = set(raw.split())
    best_match = None
    best_score = 0
    for name in candidates:
        name_words = set(name.lower().split())
        # ¿Todos los términos del input están en el nombre?
        if raw_words and raw_words.issubset(name_words):
            score = len(raw_words)
            if score > best_score:
                best_score = score
                best_match = name
    if best_match:
        return best_match

    # 3. Match por substring (fallback)
    for name in candidates:
        if raw in name.lower() or name.lower() in raw:
            return name

    return raw_input.strip()
