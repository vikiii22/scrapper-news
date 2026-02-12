"""Factor de jugadores y alineaciones."""
from typing import List, Dict, Optional
from src.models.player import Player
from src.models.match import Match

def calculate_squad_impact(
    home_missing: List[Player],
    away_missing: List[Player],
    home_key_players: List[Player], # Top 3 jugadores por rating
    away_key_players: List[Player]
) -> Dict[str, float]:
    """
    Calcula impacto de bajas importantes.
    
    El factor será positivo si favorece al local (bajas del visitante),
    y negativo si favorece al visitante (bajas del local).
    """
    home_penalty = _calculate_missing_penalty(home_missing, home_key_players)
    away_penalty = _calculate_missing_penalty(away_missing, away_key_players)
    
    # Si local tiene 2.0 penalizacion y visitante 0.0 -> Factor -2.0 (perjudica local)
    # Si visitante tiene 2.0 penalizacion -> Factor +2.0 (favorece local)
    net_impact = away_penalty - home_penalty
    
    return {
        "players_factor": round(net_impact, 2),
        "home_penalty": home_penalty,
        "away_penalty": away_penalty,
        "home_missing_count": len(home_missing),
        "away_missing_count": len(away_missing)
    }

def _calculate_missing_penalty(missing: List[Player], key_players: List[Player]) -> float:
    """Calcula penalización por jugadores faltantes."""
    penalty = 0.0
    key_ids = {p.id for p in key_players}
    
    for player in missing:
        # Base por jugador titular faltante
        impact = 0.5 
        
        # Bonus si es jugador clave (top rating)
        if player.id in key_ids:
            impact += 1.0  # Gran impacto
        elif player.rating > 7.0:
            impact += 0.5
            
        penalty += impact
        
    # Cap de penalización máxima razonable
    return min(penalty, 5.0)
