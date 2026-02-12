"""Factor de racha de resultados."""
from typing import Dict, List
from src.models.match import Match

def calculate_form_factor(
    home_team_name: str,
    away_team_name: str,
    matches: List[Match],
    last_n: int = 5
) -> float:
    """
    Calcula el factor de racha comparando la forma de ambos equipos.
    """
    form_home = _calculate_team_form(home_team_name, matches, last_n)
    form_away = _calculate_team_form(away_team_name, matches, last_n)

    # Diferencia de puntos porcentuales
    diff_percentage = form_home['percentage_points'] - form_away['percentage_points']

    # El factor es la diferencia de porcentaje escalada.
    # Una diferencia del 100% (uno gana todo, otro pierde todo) da un factor de 5.
    factor = (diff_percentage / 100) * 5
    
    return round(factor, 2)

def _calculate_team_form(team_name: str, matches: List[Match], last_n: int) -> Dict:
    """
    Calcula la forma de un solo equipo.
    """
    team_matches = [
        m for m in matches if team_name in (m.home_team.name, m.away_team.name)
    ]
    
    # Ordenar por fecha para obtener los últimos N
    team_matches.sort(key=lambda m: m.date, reverse=True)
    last_matches = team_matches[:last_n]

    if not last_matches:
        return {"points": 0, "max_points": 0, "percentage_points": 0, "form_str": ""}

    points = 0
    form_str = []
    for match in reversed(last_matches): # Invertir para leer de más antiguo a más reciente
        if match.result == 'X':
            points += 1
            form_str.append('E')
        elif (match.home_team.name == team_name and match.result == '1') or \
             (match.away_team.name == team_name and match.result == '2'):
            points += 3
            form_str.append('V')
        else:
            form_str.append('D')
            
    max_points = len(last_matches) * 3
    percentage_points = (points / max_points) * 100 if max_points > 0 else 0

    return {
        "points": points,
        "max_points": max_points,
        "percentage_points": percentage_points,
        "form_str": "".join(form_str)
    }
