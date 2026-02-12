"""Factor de posición en la tabla (Fuerza relativa)."""
from typing import Dict, List, Any

def calculate_standings_factor(
    home_team_name: str,
    away_team_name: str,
    standings: List[Dict[str, Any]]
) -> float:
    """
    Calcula un factor basado en la diferencia de posición y puntos en la tabla.
    Un valor positivo favorece al equipo local (mejor clasificado).
    """
    if not standings:
        return 0.0

    home_data = _find_team_stats(home_team_name, standings)
    away_data = _find_team_stats(away_team_name, standings)
    
    if not home_data or not away_data:
        return 0.0
        
    # --- Componente 1: Diferencia de Posición ---
    # Si Home es 1º y Away es 20º, diff = 19 -> Gran ventaja local
    # Si Home es 20º y Away es 1º, diff = -19 -> Gran ventaja visitante
    pos_diff = away_data['position'] - home_data['position']
    
    # Normalizar diferencia de posición
    # Max diff aprox 20. Queremos que un 1 vs 20 dé un factor de aprox +2.0 a +3.0
    pos_factor = (pos_diff / 20.0) * 3.0
    
    # --- Componente 2: Diferencia de Puntos ---
    # A veces las posiciones engañan, los puntos son más reales.
    points_diff = home_data['points'] - away_data['points']
    
    # Normalizar diferencia de puntos
    # Max diferencia aprox 50-60 puntos. Queremos que +50 ptos dé un factor de +3.0
    points_factor = (points_diff / 50.0) * 3.0
    
    # Promedio de ambos indicadores
    total_factor = (pos_factor + points_factor) / 2
    
    # Cap para evitar valores extremos únicos
    total_factor = max(min(total_factor, 4.0), -4.0)
    
    return round(total_factor, 2)

def _find_team_stats(team_name: str, standings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Busca estadísticas de un equipo en la tabla."""
    # Normalización simple interna
    search_name = team_name.strip().lower()
    
    for team in standings:
        t_name = str(team.get('team', '')).strip().lower()
        if not t_name: # Fallback a veces 'team_name' key
             t_name = str(team.get('team_name', '')).strip().lower()
             
        # Matching simple
        if search_name in t_name or t_name in search_name:
            return {
                'position': int(team.get('position', 10)),
                'points': int(team.get('points', 0))
            }
            
    return None
