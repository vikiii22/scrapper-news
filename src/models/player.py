"""Modelo de datos para jugadores."""
from dataclasses import dataclass
from typing import Optional

@dataclass
class Player:
    """Representa un jugador de fútbol."""
    id: int
    name: str
    position: str
    team_id: int
    rating: float = 6.0  # Rating base promedio
    goals: int = 0
    assists: int = 0
    matches_played: int = 0
    is_injured: bool = False
    is_suspended: bool = False
    
    @property
    def is_available(self) -> bool:
        """Indica si el jugador está disponible para jugar."""
        return not (self.is_injured or self.is_suspended)
