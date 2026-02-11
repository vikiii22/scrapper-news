"""Clase base para scrapers."""
from abc import ABC, abstractmethod
from typing import Any, Dict, List
import logging

class BaseScraper(ABC):
    """Clase base abstracta para todos los scrapers."""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"scraper.{name}")
    
    @abstractmethod
    def fetch(self, **kwargs) -> Dict[str, Any]:
        """Obtiene datos de la fuente."""
        pass
    
    @abstractmethod
    def parse(self, raw_data: Any) -> List[Dict]:
        """Parsea los datos obtenidos."""
        pass
    
    def run(self, **kwargs) -> List[Dict]:
        """Ejecuta el scraper completo."""
        self.logger.info(f"Iniciando {self.name}")
        raw = self.fetch(**kwargs)
        parsed = self.parse(raw)
        self.logger.info(f"Completado: {len(parsed)} items")
        return parsed
