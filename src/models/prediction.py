"""Modelo de datos para predicciones."""
from dataclasses import dataclass, field
from typing import Dict
from src.models.match import Match

@dataclass
class Prediction:
    match: Match
    prob_home: float
    prob_draw: float
    prob_away: float
    recommended_bet: str
    confidence: float
    factors: Dict[str, float] = field(default_factory=dict)
    
    @property
    def confidence_level(self) -> str:
        if self.confidence >= 70:
            return "ALTA"
        elif self.confidence >= 55:
            return "MEDIA"
        return "BAJA"
