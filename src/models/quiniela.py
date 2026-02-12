"""Modelo de datos para el boleto de la Quiniela."""
from dataclasses import dataclass
from typing import List
from src.models.prediction import Prediction

@dataclass
class QuinielaBet:
    prediction: Prediction
    bet: str # '1', 'X', '2'

@dataclass
class QuinielaTicket:
    bets: List[QuinielaBet]
    cost: float
