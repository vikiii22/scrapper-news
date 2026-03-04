"""Factor de días de descanso."""
from datetime import datetime
from typing import List, Optional, Dict, Any
from src.models.match import Match

def calculate_rest_days_factor(
    match: Match,
    historical_matches: List[Match],
    global_matches: Optional[List[Dict[str, Any]]] = None
) -> float:
    """
    Calcula un factor basado en la diferencia de días de descanso.
    Un valor positivo favorece al equipo local.
    
    Si se provee `global_matches` (partidos de todas las competiciones), 
    se usan para encontrar el partido real más reciente de cada equipo.
    De lo contrario, usa `historical_matches` (sólo liga).
    """
    
    # Check if we have global matches to use
    if global_matches:
        last_match_home_date = _get_last_global_match_date(match.home_team.name, match.date, global_matches)
        last_match_away_date = _get_last_global_match_date(match.away_team.name, match.date, global_matches)
    else:
        # Fallback to league matches
        lmh = _get_last_match_before(match.home_team.name, match.date, historical_matches)
        lma = _get_last_match_before(match.away_team.name, match.date, historical_matches)
        last_match_home_date = lmh.date if lmh else None
        last_match_away_date = lma.date if lma else None

    if not last_match_home_date or not last_match_away_date:
        return 0.0

    rest_days_home = (match.date - last_match_home_date).days
    rest_days_away = (match.date - last_match_away_date).days

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
def _get_last_global_match_date(team_name: str, date: datetime, global_matches: List[Dict[str, Any]]) -> Optional[datetime]:
    """
    Encuentra la fecha del último partido real en cualquier competición en base a la lista global.
    Asume que global_matches son diccionarios devueltos por el scraper.
    """
    team_name_lower = team_name.lower()
    team_matches = []
    
    for m in global_matches:
        home_name = str(m.get('home_team_name', '')).lower()
        away_name = str(m.get('away_team_name', '')).lower()
        
        # Básicamente comprobamos si el equipo jugó este partido
        # a veces los nombres varían un poco (ej: "Real Madrid" vs "Real Madrid CF")
        # Por simplicidad aquí hacemos 'in' o ==
        if team_name_lower in home_name or team_name_lower in away_name or home_name in team_name_lower or away_name in team_name_lower:
            try:
                m_date = datetime.fromisoformat(m['date'])
                if m_date < date:
                    team_matches.append(m_date)
            except (ValueError, TypeError, KeyError):
                pass
                
    if not team_matches:
        return None
        
    team_matches.sort(reverse=True)
    return team_matches[0]
