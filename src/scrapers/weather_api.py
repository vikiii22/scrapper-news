"""Cliente para obtener datos meteorológicos."""
import logging
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
import requests
from datetime import datetime

# TODO: Mover a settings o variables de entorno
API_KEY = "dummy_key_for_now"
BASE_URL = "https://api.openweathermap.org/data/2.5/forecast"

@dataclass
class WeatherCondition:
    temp: float
    rain_mm: float
    wind_speed: float
    condition: str  # Clear, Rain, Clouds, etc.

class WeatherClient:
    """Cliente para la API de clima."""
    
    def __init__(self, api_key: str = API_KEY):
        self.api_key = api_key
        self.logger = logging.getLogger("scraper.weather")
        
    def get_forecast(self, city: str, date: datetime) -> Optional[WeatherCondition]:
        """
        Obtiene pronóstico para una ciudad y fecha.
        
        Args:
            city: Nombre de la ciudad
            date: Fecha del partido
        """
        self.logger.info(f"Obteniendo clima para {city} en {date}")
        
        # Simulacion para demo sin API key real
        # En prod: param q={city}, appid={api_key}
        if date.date() < datetime.now().date():
             self.logger.warning("No hay pronóstico histórico disponible gratis")
             return None
             
        # Logica mockeada para no fallar sin API Key
        return WeatherCondition(
            temp=18.0,
            rain_mm=0.0,
            wind_speed=10.0,
            condition="Clear"
        )
