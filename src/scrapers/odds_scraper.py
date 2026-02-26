"""Scraper de cuotas de apuestas para La Quiniela.

Fuentes (en orden de preferencia):
1. The Odds API (gratuita — 500 llamadas/mes): https://the-odds-api.com
   - No requiere Playwright, simple REST con requests.
2. Fallback: Cuotas del boleto de La Quiniela (si se detectan en el HTML).

Uso:
    from src.scrapers.odds_scraper import OddsScraper
    scraper = OddsScraper(api_key="tu_key")
    odds = scraper.get_odds_for_match("Barcelona", "Real Madrid")
    # {"1": 1.45, "X": 4.20, "2": 6.50} — cuotas decimales
"""
import json
import logging
from pathlib import Path
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta

from src.scrapers.base import BaseScraper
from src.config.settings import ODDS_API_KEY, RAW_DATA_DIR

logger = logging.getLogger("scraper.odds")


class OddsScraper(BaseScraper):
    """Scraper de cuotas de casas de apuestas.
    
    Obtiene cuotas 1X2 de encuentros de fútbol usando The Odds API.
    Si no hay API key, devuelve datos vacíos sin errores (el predictor
    seguirá funcionando solo con el modelo Poisson + factores).
    """

    ODDS_API_BASE = "https://api.the-odds-api.com/v4"
    SPORTS = {
        "la_liga": "soccer_spain_la_liga",
        "segunda": "soccer_spain_segunda_division",
    }
    CACHE_FILE = RAW_DATA_DIR / "odds_cache.json"
    CACHE_TTL_HOURS = 4  # Cuotas cambian frecuentemente, TTL corto

    def __init__(self, api_key: Optional[str] = None):
        super().__init__("OddsScraper")
        self.api_key = api_key or ODDS_API_KEY
        self._cache: Dict[str, Any] = self._load_cache()

    def _load_cache(self) -> Dict:
        """Carga caché de cuotas del disco."""
        try:
            if self.CACHE_FILE.exists():
                with open(self.CACHE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
        return {}

    def _save_cache(self) -> None:
        """Persiste caché de cuotas al disco."""
        try:
            self.CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(self.CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, ensure_ascii=False, indent=2)
        except IOError as e:
            logger.warning(f"No se pudo guardar caché de cuotas: {e}")

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Verifica si los datos en caché siguen siendo válidos."""
        entry = self._cache.get(cache_key)
        if not entry or "timestamp" not in entry:
            return False
        cached_at = datetime.fromisoformat(entry["timestamp"])
        return datetime.now() - cached_at < timedelta(hours=self.CACHE_TTL_HOURS)

    def get_all_odds(self, league: str = "la_liga") -> List[Dict]:
        """Obtiene todas las cuotas del próximo ciclo de partidos de una liga.
        
        Returns:
            Lista de partidos con cuotas: [
                {
                    "home_team": "FC Barcelona",
                    "away_team": "Real Madrid",
                    "odds": {"1": 1.45, "X": 4.20, "2": 6.50}
                },
                ...
            ]
        """
        cache_key = f"odds_{league}"

        if self._is_cache_valid(cache_key):
            logger.info(f"Usando cuotas en caché para {league}")
            return self._cache[cache_key]["data"]

        if not self.api_key:
            logger.warning(
                "No hay ODDS_API_KEY configurada. Las cuotas no se usarán. "
                "Para activarlas, registra en https://the-odds-api.com y añade "
                "ODDS_API_KEY en tu archivo .env"
            )
            return []

        sport = self.SPORTS.get(league, self.SPORTS["la_liga"])
        url = (
            f"{self.ODDS_API_BASE}/sports/{sport}/odds"
            f"?apiKey={self.api_key}"
            f"&regions=eu"
            f"&markets=h2h"
            f"&oddsFormat=decimal"
            f"&dateFormat=iso"
        )

        try:
            from src.utils.http_client import http_client
            response = http_client.get(url, timeout=15)
            response.raise_for_status()
            raw_events = response.json()
            parsed = self._parse_odds_api_response(raw_events)

            self._cache[cache_key] = {
                "timestamp": datetime.now().isoformat(),
                "data": parsed
            }
            self._save_cache()
            logger.info(f"Obtenidas cuotas para {len(parsed)} partidos de {league}")
            return parsed

        except Exception as e:
            logger.error(f"Error obteniendo cuotas de The Odds API: {e}")
            return []

    def _parse_odds_api_response(self, events: List[Dict]) -> List[Dict]:
        """Parsea la respuesta de The Odds API al formato interno."""
        results = []
        for event in events:
            home = event.get("home_team", "")
            away = event.get("away_team", "")
            bookmakers = event.get("bookmakers", [])

            if not bookmakers:
                continue

            # Promediar cuotas de todos los bookmakers disponibles
            odds_1 = []
            odds_x = []
            odds_2 = []

            for bm in bookmakers:
                for market in bm.get("markets", []):
                    if market.get("key") != "h2h":
                        continue
                    for outcome in market.get("outcomes", []):
                        name = outcome.get("name", "")
                        price = outcome.get("price", 0)
                        if price <= 1.0:
                            continue
                        if name == home:
                            odds_1.append(price)
                        elif name == away:
                            odds_2.append(price)
                        elif name == "Draw":
                            odds_x.append(price)

            if odds_1 and odds_x and odds_2:
                results.append({
                    "home_team": home,
                    "away_team": away,
                    "odds": {
                        "1": round(sum(odds_1) / len(odds_1), 3),
                        "X": round(sum(odds_x) / len(odds_x), 3),
                        "2": round(sum(odds_2) / len(odds_2), 3),
                    },
                    "commence_time": event.get("commence_time", ""),
                })

        return results

    def get_odds_for_match(
        self,
        home_team: str,
        away_team: str,
        league: str = "la_liga"
    ) -> Optional[Dict[str, float]]:
        """Obtiene cuotas para un partido específico.
        
        Hace fuzzy matching por nombre de equipo (insensible a mayúsculas
        y artículos como 'FC', 'CF', 'UD', etc.).
        
        Returns:
            {"1": 1.45, "X": 4.20, "2": 6.50} o None si no se encontró.
        """
        all_odds = self.get_all_odds(league)
        if not all_odds:
            return None

        home_norm = _normalize_team_name(home_team)
        away_norm = _normalize_team_name(away_team)

        for event in all_odds:
            ev_home = _normalize_team_name(event.get("home_team", ""))
            ev_away = _normalize_team_name(event.get("away_team", ""))

            if home_norm in ev_home or ev_home in home_norm:
                if away_norm in ev_away or ev_away in away_norm:
                    return event["odds"]

        logger.debug(f"No se encontraron cuotas para: {home_team} vs {away_team}")
        return None

    def fetch(self, **kwargs) -> Dict:
        return {}

    def parse(self, raw_data: Any) -> List[Dict]:
        return []


def _normalize_team_name(name: str) -> str:
    """Normaliza un nombre de equipo para comparación fuzzy."""
    prefixes = ["fc ", "cf ", "ud ", "rcd ", "sd ", "ca ", "cd ", "real ", "atletico "]
    n = name.lower().strip()
    for p in prefixes:
        if n.startswith(p):
            n = n[len(p):]
    return n
