"""Factor de enfrentamientos directos (Head-to-Head) con contexto de localía.

Mejora sobre v1: el H2H ahora distingue si las victorias fueron en casa o fuera.
- H2H General (60%): dominio histórico independientemente del campo.
- H2H en casa del local actual (40%): cuántas veces el local actual ganó JUGANDO EN SU CASA.
"""
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

    h2h_matches.sort(key=lambda m: m.date, reverse=True)
    last_h2h = h2h_matches[:last_n]

    if not last_h2h:
        return 0.0

    # --- Componente 1: H2H General (independiente del estadio) ---
    home_wins_general = 0
    away_wins_general = 0

    for match in last_h2h:
        if (match.home_team.name == home_team_name and match.result == '1') or \
           (match.away_team.name == home_team_name and match.result == '2'):
            home_wins_general += 1
        elif (match.home_team.name == away_team_name and match.result == '1') or \
             (match.away_team.name == away_team_name and match.result == '2'):
            away_wins_general += 1

    dominance_general = (home_wins_general - away_wins_general) / len(last_h2h)
    factor_general = dominance_general * 3.0  # rango aprox -3..+3

    # --- Componente 2: H2H en Casa del Local Actual ---
    # Solo los partidos donde 'home_team_name' era el equipo local
    home_venue_matches = [
        m for m in last_h2h if m.home_team.name == home_team_name
    ]

    factor_venue = 0.0
    if home_venue_matches:
        home_wins_venue = sum(1 for m in home_venue_matches if m.result == '1')
        away_wins_venue = sum(1 for m in home_venue_matches if m.result == '2')
        dominance_venue = (home_wins_venue - away_wins_venue) / len(home_venue_matches)
        factor_venue = dominance_venue * 3.0

    # --- Combinar: 60% general + 40% en casa ---
    factor = 0.60 * factor_general + 0.40 * factor_venue

    return round(factor, 2)
