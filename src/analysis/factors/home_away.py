"""Factor de rendimiento local/visitante."""
from typing import Dict, List
from src.models.match import Match

def calculate_home_away_factor(
    team_name: str,
    matches: List[Match],
    is_home: bool,
    min_matches: int = 3
) -> Dict[str, float]:
    """
    Calcula el factor de rendimiento como local o visitante.
    
    Args:
        team_name: Nombre del equipo
        matches: Lista de partidos históricos
        is_home: True si juega en casa
        min_matches: Mínimo de partidos para calcular
        
    Returns:
        Dict con 'factor', 'wins', 'draws', 'losses', 'win_rate'
    """
    relevant_matches = [
        m for m in matches 
        if (is_home and m.home_team.name == team_name) or
           (not is_home and m.away_team.name == team_name)
    ]
    
    if len(relevant_matches) < min_matches:
        return {"factor": 0.0, "insufficient_data": True}
    
    wins = sum(1 for m in relevant_matches if _is_win(m, team_name, is_home))
    draws = sum(1 for m in relevant_matches if m.result == "X")
    losses = len(relevant_matches) - wins - draws
    
    win_rate = wins / len(relevant_matches)
    
    # Factor: diferencia respecto al 33% base
    base_rate = 0.33
    factor = (win_rate - base_rate) * 15  # Escalar a ±5 puntos máx
    
    return {
        "factor": round(factor, 2),
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "win_rate": round(win_rate * 100, 1),
        "matches_analyzed": len(relevant_matches)
    }

def _is_win(match: Match, team_name: str, is_home: bool) -> bool:
    """Determina si el equipo ganó el partido."""
    if match.result is None:
        return False
    if is_home:
        return match.result == "1"
    return match.result == "2"
