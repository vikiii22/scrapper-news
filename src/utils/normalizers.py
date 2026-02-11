"""Utilidades para normalizar nombres de equipos."""
from typing import Dict

TEAM_NAME_MAPPINGS = {
    "Atlético Madrid": "Atletico Madrid",
    "Real Betis": "Betis",
    "Cádiz": "Cadiz",
    "Deportivo Alavés": "Alaves",
    "Leganés": "Leganes",
    # ... y así sucesivamente
}

def normalize_team_name(name: str) -> str:
    """Normaliza el nombre de un equipo."""
    return TEAM_NAME_MAPPINGS.get(name, name)
