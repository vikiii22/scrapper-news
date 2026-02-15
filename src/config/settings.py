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
    "la_liga": LeagueConfig(id=8, season_id=77559, name="La Liga", country="Spain"),
    "segunda": LeagueConfig(id=54, season_id=77558, name="Segunda División", country="Spain"),
}

# Factores de predicción
FACTOR_WEIGHTS = {
    "home_advantage": 1.0,
    "away_performance": -1.0,
    "standings": 2.5, # Factor de calidad/posición
    "form": 0.8,
    "h2h": 0.6,
    "weather": 0.3,
    "players": 0.4,
}

# Límites
MIN_MATCHES_ANALYSIS = 5
MAX_MATCHES_HISTORY = 10

# Configuración del modelo Poisson
DRAW_PROB_LA_LIGA = 0.25
DRAW_PROB_HYPERMOTION = 0.27
HOME_ADVANTAGE_GOALS = 0.37
INJURY_PENALTY_THRESHOLD = 7.5
INJURY_PENALTY_AMOUNT = 0.15  # 15% de penalización en ataque
NEUTRAL_GROUND_TERMS = ["neutral", "estadio neutral", "neutral ground"]

