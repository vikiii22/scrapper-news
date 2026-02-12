"""Factor meteorológico para análisis de partidos."""
from typing import Dict, Any, Optional
from src.models.match import Match
from src.scrapers.weather_api import WeatherCondition

def calculate_weather_impact(match: Match, weather_data: Optional[WeatherCondition]) -> Dict[str, float]:
    """
    Calcula el impacto del clima en el resultado probable.
    
    Args:
        match: Datos del partido
        weather_data: Condiciones climáticas previstas
        
    Returns:
        Dict con factor de ajuste y metadatos
    """
    if not weather_data:
        return {"weather_factor": 0.0, "condition": "unknown"}
        
    factor = 0.0
    impact_description = []
    
    # Lluvia intensa (> 5mm) suele igualar el juego (favorece empates o equipos defensivos)
    if weather_data.rain_mm > 5.0:
        factor -= 0.5  # Reduce ligeramente probabilidad de victoria clara local
        impact_description.append("rain_heavy")
    elif weather_data.rain_mm > 0.5:
        factor -= 0.2
        impact_description.append("rain_light")
        
    # Viento fuerte (> 30 km/h) hace el juego impredecible
    if weather_data.wind_speed > 30.0:
        factor *= 0.8 # Reduce confianza
        impact_description.append("wind_strong")
        
    # Temperaturas extremas
    if weather_data.temp > 35.0:
        factor += 0.2 # Local (aclimatado) suele tener ventaja
        impact_description.append("heat_extreme")
    elif weather_data.temp < 0.0:
        impact_description.append("cold_extreme")
        
    return {
        "weather_factor": round(factor, 2),
        "condition": weather_data.condition,
        "rain_mm": weather_data.rain_mm,
        "impacts": impact_description
    }
