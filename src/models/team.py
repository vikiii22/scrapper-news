"""Modelo de datos para equipos."""
from dataclasses import dataclass
from typing import Optional

@dataclass
class Team:
    id: int
    name: str
    short_name: Optional[str] = None
