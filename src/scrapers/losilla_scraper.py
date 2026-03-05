"""Scraper de porcentajes de La Quiniela desde la API de EduardoLosilla.es

Fuentes (todas son APIs REST públicas, sin autenticación):
- porcentajes_quinielista → %Jugados: apuestas de la comunidad por cada signo
- porcentajes_lae          → %LAE: datos oficiales de LAE (Loterías y Apuestas del Estado)
- probabilidad_real         → %Probables: probabilidad estadística basada en datos de liga

Uso:
    from src.scrapers.losilla_scraper import LosillaScraper
    scraper = LosillaScraper()
    data = scraper.get_all_percentages(jornada=46, temporada=2026)
    # data = {
    #   1: {"jugados": {"1": 22.34, "X": 33.01, "2": 44.65}, "lae": {...}, "probables": {...}},
    #   ...
    #   15: {"jugados": {"local_0": ..., ...}, "lae": {...}, "probables": {...}}  # Pleno al 15
    # }
"""
import json
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from src.scrapers.base import BaseScraper
from src.config.settings import RAW_DATA_DIR

logger = logging.getLogger("scraper.losilla")

API_BASE = "https://api.eduardolosilla.es/servicios/v1"
CACHE_FILE = RAW_DATA_DIR / "losilla_cache.json"
CACHE_TTL_HOURS = 1  # Los porcentajes se actualizan frecuentemente


class LosillaScraper(BaseScraper):
    """Scraper de porcentajes de la Quiniela desde eduardolosilla.es.

    Obtiene los tres tipos de porcentajes disponibles para la jornada actual:
    - %Jugados: porcentaje de apuestas de la comunidad quinielista por signo
    - %LAE: datos oficiales de Loterías y Apuestas del Estado
    - %Probables: probabilidad estadística basada en datos reales de liga

    Si la API no está disponible, devuelve un dict vacío sin interrumpir el pipeline.
    Implementa caché JSON con TTL de 1 hora para minimizar peticiones.
    """

    def __init__(self):
        super().__init__("LosillaScraper")
        self._cache: Dict[str, Any] = self._load_cache()

    # ------------------------------------------------------------------ #
    #  Caché                                                               #
    # ------------------------------------------------------------------ #

    def _load_cache(self) -> Dict:
        try:
            if CACHE_FILE.exists():
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
        return {}

    def _save_cache(self) -> None:
        try:
            CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, ensure_ascii=False, indent=2)
        except IOError as e:
            logger.warning(f"No se pudo guardar caché de Losilla: {e}")

    def _is_cache_valid(self, cache_key: str) -> bool:
        entry = self._cache.get(cache_key)
        if not entry or "timestamp" not in entry:
            return False
        cached_at = datetime.fromisoformat(entry["timestamp"])
        return datetime.now() - cached_at < timedelta(hours=CACHE_TTL_HOURS)

    # ------------------------------------------------------------------ #
    #  API pública                                                         #
    # ------------------------------------------------------------------ #

    def get_all_percentages(
        self, jornada: int, temporada: int
    ) -> Dict[int, Dict[str, Dict[str, float]]]:
        """Obtiene los 3 tipos de porcentajes para todos los partidos de la jornada.

        Returns:
            dict indexado por número de partido (1-15):
            {
                1: {
                    "jugados":   {"1": 22.34, "X": 33.01, "2": 44.65},
                    "lae":       {"1": 28.0,  "X": 30.0,  "2": 42.0},
                    "probables": {"1": 33.41, "X": 32.83, "2": 33.76},
                },
                ...
                15: {
                    # Partido especial "Pleno al 15" — goles del partido
                    "jugados":   {"local_0": 27, "local_1": 53, ..., "visit_M": 52},
                    "lae":       {...},
                    "probables": {"local_0": 38, "local_1": 37, ...},
                }
            }
        """
        cache_key = f"losilla_{jornada}_{temporada}"
        if self._is_cache_valid(cache_key):
            logger.info(f"Usando porcentajes Losilla en caché (j{jornada}/{temporada})")
            raw = self._cache[cache_key]["data"]
            return {int(k): v for k, v in raw.items()}

        jugados = self._fetch_xml_percentages("porcentajes_quinielista", jornada, temporada)
        lae = self._fetch_xml_percentages("porcentajes_lae", jornada, temporada)
        probables = self._fetch_csv_probabilities(jornada, temporada)

        result: Dict[int, Dict] = {}
        all_nums = set(jugados.keys()) | set(lae.keys()) | set(probables.keys())
        for num in all_nums:
            result[num] = {
                "jugados": jugados.get(num, {}),
                "lae": lae.get(num, {}),
                "probables": probables.get(num, {}),
            }

        if result:
            self._cache[cache_key] = {
                "timestamp": datetime.now().isoformat(),
                "data": {str(k): v for k, v in result.items()},
            }
            self._save_cache()
            logger.info(f"Obtenidos porcentajes Losilla para {len(result)} partidos")

        return result

    # ------------------------------------------------------------------ #
    #  Fetching y parseo                                                   #
    # ------------------------------------------------------------------ #

    def _fetch_xml_percentages(
        self, endpoint: str, jornada: int, temporada: int
    ) -> Dict[int, Dict[str, float]]:
        """Parsea cualquiera de los endpoints XML de porcentajes."""
        url = f"{API_BASE}/{endpoint}?jornada={jornada}&temporada={temporada}"
        try:
            from src.utils.http_client import http_client
            resp = http_client.get(url, timeout=10)
            resp.raise_for_status()
            return _parse_xml_percentages(resp.text)
        except Exception as e:
            logger.warning(f"Error obteniendo {endpoint} (j{jornada}): {e}")
            return {}

    def _fetch_csv_probabilities(
        self, jornada: int, temporada: int
    ) -> Dict[int, Dict[str, float]]:
        """Parsea el endpoint CSV de probabilidad_real."""
        url = f"{API_BASE}/probabilidad_real?jornada={jornada}&temporada={temporada}&csv=true"
        try:
            from src.utils.http_client import http_client
            resp = http_client.get(url, timeout=10)
            resp.raise_for_status()
            return _parse_csv_probabilities(resp.text)
        except Exception as e:
            logger.warning(f"Error obteniendo probabilidad_real (j{jornada}): {e}")
            return {}

    # ------------------------------------------------------------------ #
    #  BaseScraper contract                                                #
    # ------------------------------------------------------------------ #

    def fetch(self, **kwargs) -> Dict:
        return {}

    def parse(self, raw_data: Any) -> Dict:
        return {}


# ------------------------------------------------------------------ #
#  Funciones de parseo (standalone para facilitar los tests)          #
# ------------------------------------------------------------------ #

def _parse_xml_percentages(xml_text: str) -> Dict[int, Dict[str, float]]:
    """Parsea la respuesta XML de porcentajes_quinielista o porcentajes_lae.

    Formato XML:
        <partido num="1" local="GETAFE" visitante="BETIS"
                 porc_1="22.34" porc_X="33.01" porc_2="44.65"/>
        ...
        <!-- Partido 15 especial: -->
        <partido num="15" local="ATH.CLUB" visitante="BARCELONA"
                 porc_15L_0="26.37" porc_15L_1="52.75" porc_15L_2="16.41" porc_15L_M="4.47"
                 porc_15V_0="3.44"  porc_15V_1="14.2"  porc_15V_2="30.61" porc_15V_M="51.75"/>
    """
    result: Dict[int, Dict[str, float]] = {}
    try:
        root = ET.fromstring(xml_text)
        # El nodo partidos puede estar anidado (<quinielista><porcentajes><partido .../>)
        partidos = root.iter("partido")
        for partido in partidos:
            num = int(partido.get("num", 0))
            if num == 0:
                continue
            if num == 15:
                # Partido especial Pleno al 15
                result[15] = _extract_pleno15_xml(partido)
            else:
                data: Dict[str, float] = {}
                for sign, attr in [("1", "porc_1"), ("X", "porc_X"), ("2", "porc_2")]:
                    val = partido.get(attr)
                    if val is not None:
                        try:
                            data[sign] = float(val)
                        except ValueError:
                            pass
                if data:
                    result[num] = data
    except ET.ParseError as e:
        logger.error(f"Error parseando XML de Losilla: {e}")
    return result


def _extract_pleno15_xml(partido) -> Dict[str, float]:
    """Extrae los atributos especiales del partido 15 (Pleno al 15)."""
    mapping = {
        "local_0": "porc_15L_0",
        "local_1": "porc_15L_1",
        "local_2": "porc_15L_2",
        "local_M": "porc_15L_M",
        "visit_0": "porc_15V_0",
        "visit_1": "porc_15V_1",
        "visit_2": "porc_15V_2",
        "visit_M": "porc_15V_M",
    }
    data: Dict[str, float] = {}
    for key, attr in mapping.items():
        val = partido.get(attr)
        if val is not None:
            try:
                data[key] = float(val)
            except ValueError:
                pass
    return data


def _parse_csv_probabilities(csv_text: str) -> Dict[int, Dict[str, float]]:
    """Parsea la respuesta CSV de probabilidad_real.

    Formato CSV (separador ';', decimales con coma):
        1;GETAFE-BETIS;33,41;32,83;33,76
        ...
        15;ATH.CLUB-BARCELONA;38,28;36,76;17,65;7,31;15,31;28,73;26,96;29
    """
    result: Dict[int, Dict[str, float]] = {}
    for line in csv_text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(";")
        if len(parts) < 4:
            continue
        try:
            num = int(parts[0])
        except ValueError:
            continue

        def _to_float(s: str) -> float:
            return float(s.replace(",", "."))

        if num == 15 and len(parts) >= 9:
            # 8 valores: local_0, local_1, local_2, local_M, visit_0, visit_1, visit_2, visit_M
            try:
                result[15] = {
                    "local_0": _to_float(parts[2]),
                    "local_1": _to_float(parts[3]),
                    "local_2": _to_float(parts[4]),
                    "local_M": _to_float(parts[5]),
                    "visit_0": _to_float(parts[6]),
                    "visit_1": _to_float(parts[7]),
                    "visit_2": _to_float(parts[8]),
                    "visit_M": _to_float(parts[9]) if len(parts) > 9 else 0.0,
                }
            except (ValueError, IndexError):
                pass
        elif len(parts) >= 4:
            try:
                result[num] = {
                    "1": _to_float(parts[2]),
                    "X": _to_float(parts[3]),
                    "2": _to_float(parts[4]) if len(parts) > 4 else 0.0,
                }
            except ValueError:
                pass
    return result


def detect_current_round(temporada: int) -> int:
    """Intenta detectar la jornada actual desde MongoDB, o devuelve un valor por defecto."""
    try:
        from src.utils.mongo_loader import load_mongo_data
        predictions = load_mongo_data("quiniela_matches")
        if predictions and isinstance(predictions, list) and len(predictions) > 0:
            jornada = predictions[0].get("jornada")
            if jornada:
                return int(jornada)
    except Exception:
        pass
    # Fallback: jornada 1 (el usuario la ajusta manualmente si es necesario)
    logger.warning("No se pudo detectar la jornada actual automáticamente. Usar jornada=1.")
    return 1
