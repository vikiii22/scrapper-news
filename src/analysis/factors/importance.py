"""Factor de importancia del partido."""
from typing import Dict, List

def calculate_importance_factor(
    home_team_name: str,
    away_team_name: str,
    standings: List[Dict]
) -> float:
    """
    Calcula un factor basado en la importancia del partido para cada equipo.
    Un valor positivo significa que el partido es más importante para el equipo local.
    """
    if not standings:
        return 0.0

    home_importance = _get_team_importance(home_team_name, standings)
    away_importance = _get_team_importance(away_team_name, standings)

    # La diferencia de "puntos de importancia" es el factor
    factor = home_importance['importance_points'] - away_importance['importance_points']
    
    return round(factor, 2)

def _get_team_importance(team_name: str, standings: List[Dict]) -> Dict:
    """
    Determina la importancia del partido para un equipo basado en su posición.
    """
    team_standing = None
    for team in standings:
        # Suponiendo que 'team_name' es una clave en el diccionario de la clasificación
        if team.get('team_name') == team_name:
            team_standing = team
            break
    
    if not team_standing:
        return {"importance_level": "unknown", "importance_points": 0}

    position = team_standing.get('position', 10)
    total_teams = len(standings)
    
    # Zonas críticas
    champions_zone = 4
    europa_zone = 7
    relegation_zone = total_teams - 3

    importance_points = 0
    importance_level = "normal"

    # Lucha por el título
    if position <= 2:
        importance_points = 3.0
        importance_level = "title_race"
    # Lucha por Champions
    elif position <= champions_zone + 1:
        importance_points = 2.0
        importance_level = "champions_league_spot"
    # Lucha por Europa
    elif position <= europa_zone + 2:
        importance_points = 1.5
        importance_level = "europa_league_spot"
    # Lucha por no descender
    elif position >= relegation_zone - 1:
        importance_points = 2.5
        importance_level = "relegation_battle"
    # Zona media-baja, cerca del descenso
    elif position >= relegation_zone - 3:
        importance_points = 1.0
        importance_level = "avoiding_relegation"
    
    return {
        "importance_level": importance_level,
        "importance_points": importance_points
    }
