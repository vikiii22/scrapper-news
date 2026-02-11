"""Factor de enfrentamientos directos (Head-to-Head)."""
from typing import Dict, List
from src.models.match import Match

def calculate_h2h_factor(
    home_team_name: str,
    away_team_name: str,
    matches: List[Match],
    last_n: int = 10
) -> float:
    """
    Calcula un factor basado en los enfrentamientos directos históricos.
    Un valor positivo favorece al equipo local, negativo al visitante.
    """
    h2h_matches = [
        m for m in matches
        if (home_team_name in (m.home_team.name, m.away_team.name) and
            away_team_name in (m.home_team.name, m.away_team.name))
    ]

    # Ordenar por fecha y tomar los últimos N
    h2h_matches.sort(key=lambda m: m.date, reverse=True)
    last_h2h = h2h_matches[:last_n]

    if not last_h2h:
        return 0.0

    home_wins = 0
    away_wins = 0

    for match in last_h2h:
        if (match.home_team.name == home_team_name and match.result == '1') or \
           (match.away_team.name == home_team_name and match.result == '2'):
            home_wins += 1
        elif (match.home_team.name == away_team_name and match.result == '1') or \
             (match.away_team.name == away_team_name and match.result == '2'):
            away_wins += 1

    # Calcular el dominio como la diferencia de victorias sobre el total de partidos
    dominance = (home_wins - away_wins) / len(last_h2h)

    # Escalar el factor, por ejemplo, a un rango de -3 a +3
    factor = dominance * 3
    
    return round(factor, 2)
