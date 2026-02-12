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
    
    # Eliminamos el retorno temprano si hay pocos datos y dejamos que el smoothing actúe
    # if len(relevant_matches) < min_matches:
    #    return {"factor": 0.0, "insufficient_data": True}
    
    wins = sum(1 for m in relevant_matches if _is_win(m, team_name, is_home))
    draws = sum(1 for m in relevant_matches if m.result == "X")
    losses = len(relevant_matches) - wins - draws
    
    # Usar Laplace smoothing para evitar extremos con pocos datos
    # Añadimos 1 victoria, 1 empate y 1 derrota "virtuales"
    virtual_matches = 3
    smoothed_wins = wins + 1
    
    smoothed_total = len(relevant_matches) + virtual_matches
    
    # Tasa de victorias suavizada
    win_rate = smoothed_wins / smoothed_total
    
    # Tasa base de referencia (ej. 40% local, 25% visitante)
    base_rate = 0.40 if is_home else 0.25
    
    # Factor: diferencia respecto a la base
    # Reducimos multiplicador (de 15 a 8) para suavizar
    factor = (win_rate - base_rate) * 8
    
    # Limitar el factor entre -5 y 5
    factor = max(min(factor, 5.0), -5.0)
    
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
