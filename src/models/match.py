"""Modelo de datos para partidos."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict
from enum import Enum

class MatchStatus(Enum):
    SCHEDULED = "scheduled"
    LIVE = "live"
    FINISHED = "finished"
    POSTPONED = "postponed"

@dataclass
class Team:
    id: int
    name: str
    short_name: Optional[str] = None
    
@dataclass
class Match:
    id: int
    home_team: Team
    away_team: Team
    date: datetime
    league: str
    status: MatchStatus = MatchStatus.SCHEDULED
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    venue: Optional[str] = None
    round: Optional[int] = None
    
    @property
    def result(self) -> Optional[str]:
        """Retorna '1', 'X', o '2' según el resultado."""
        if self.home_score is None or self.away_score is None:
            return None
        if self.home_score > self.away_score:
            return "1"
        elif self.home_score < self.away_score:
            return "2"
        return "X"
