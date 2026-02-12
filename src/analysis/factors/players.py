"""Factor de jugadores y alineaciones."""
from typing import List, Dict, Optional
import statistics
from src.models.player import Player
from src.models.match import Match

def calculate_squad_strength(
    home_lineup: List[Player],
    away_lineup: List[Player]
) -> Dict[str, float]:
    """
    Compara la fuerza de las alineaciones disponibles.
    Devuelve un factor positivo si el local es mejor, negativo si el visitante es mejor.
    """
    if not home_lineup or not away_lineup:
        return {"strength_factor": 0.0, "home_rating": 0.0, "away_rating": 0.0}

    # Calcular rating promedio de la alineación (Top 11 para filtrar suplentes si vienen todos)
    # Asumimos que la lista trae los disponibles. Ordenamos por rating descendente.
    home_ratings = sorted([p.rating for p in home_lineup if p.rating > 0], reverse=True)[:11]
    away_ratings = sorted([p.rating for p in away_lineup if p.rating > 0], reverse=True)[:11]
    
    if not home_ratings or not away_ratings:
        return {"strength_factor": 0.0, "home_rating": 0.0, "away_rating": 0.0}

    avg_home = statistics.mean(home_ratings)
    avg_away = statistics.mean(away_ratings)
    
    # Diferencia de rating
    diff = avg_home - avg_away
    
    # Escalar diferencia. 
    # Ej: 7.2 vs 6.8 (diff 0.4) -> Factor significativo.
    # Un factor de 1.0 debería representar una ventaja clara.
    # Usemos un multiplicador de 3.0
    factor = diff * 3.0
    
    # Cap para evitar extremos
    factor = max(min(factor, 3.0), -3.0)
    
    return {
        "strength_factor": round(factor, 2),
        "home_avg_rating": round(avg_home, 2),
        "away_avg_rating": round(avg_away, 2)
    }

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
