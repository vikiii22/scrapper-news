"""Configuración global del proyecto."""
from pathlib import Path
from dataclasses import dataclass

# Rutas
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

# APIs
SOFASCORE_BASE_URL = "https://api.sofascore.com/api/v1"

# Ligas
@dataclass
class LeagueConfig:
    id: int
    season_id: int
    name: str
    country: str

LEAGUES = {
    "la_liga": LeagueConfig(id=54, season_id=77558, name="La Liga", country="Spain"),
    "segunda": LeagueConfig(id=55, season_id=77559, name="Segunda División", country="Spain"),
}

# Factores de predicción
FACTOR_WEIGHTS = {
    "home_advantage": 5.0,
    "away_performance": -5.0,
    "form": 3.0,
    "h2h": 2.0,
    "rest_days": 1.5,
    "importance": 2.0,
}
