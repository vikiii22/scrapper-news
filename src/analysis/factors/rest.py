"""Factor de días de descanso."""
from datetime import datetime
from typing import List, Optional
from src.models.match import Match

def calculate_rest_days_factor(
    match: Match,
    historical_matches: List[Match]
) -> float:
    """
    Calcula un factor basado en la diferencia de días de descanso.
    Un valor positivo favorece al equipo local.
    """
    
    last_match_home = _get_last_match_before(match.home_team.name, match.date, historical_matches)
    last_match_away = _get_last_match_before(match.away_team.name, match.date, historical_matches)

    if not last_match_home or not last_match_away:
        return 0.0

    rest_days_home = (match.date - last_match_home.date).days
    rest_days_away = (match.date - last_match_away.date).days

    diff_days = rest_days_home - rest_days_away
    
    factor = 0.0
    # Ventaja si la diferencia es significativa
    if diff_days >= 3:
        factor = 1.5
    elif diff_days >= 2:
        factor = 0.75
    elif diff_days <= -3:
        factor = -1.5
    elif diff_days <= -2:
        factor = -0.75

    # Penalización por muy poco descanso (< 3 días)
    if rest_days_home < 3:
        factor -= 1.0
    if rest_days_away < 3:
        factor += 1.0
        
    return round(factor, 2)

def _get_last_match_before(team_name: str, date: datetime, matches: List[Match]) -> Optional[Match]:
    """
    Encuentra el último partido de un equipo antes de una fecha dada.
    """
    team_matches = [
        m for m in matches 
        if (team_name in (m.home_team.name, m.away_team.name)) and m.date < date
    ]
    
    if not team_matches:
        return None
        
    team_matches.sort(key=lambda m: m.date, reverse=True)
    return team_matches[0]
