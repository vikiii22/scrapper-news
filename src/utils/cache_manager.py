"""Gestor de caché persistente para datos del predictor de Quiniela.

Reduce llamadas innecesarias a SofaScore y riesgo de bloqueo de IP.
Almacena clasificaciones y partidos históricos en SQLite (integridad referencial)
y cuotas/noticias en JSON (datos más volátiles).

Uso:
    from src.utils.cache_manager import CacheManager
    cache = CacheManager()

    # Guardar
    cache.set("la_liga_standings", standings_list, ttl_hours=6)

    # Leer (devuelve None si expirado o inexistente)
    data = cache.get("la_liga_standings")
"""
import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from src.config.settings import CACHE_DB_PATH, CACHE_TTL_HOURS

logger = logging.getLogger("utils.cache")


class CacheManager:
    """Caché persistente con TTL usando SQLite.
    
    La base de datos tiene una única tabla 'cache' con:
        key      TEXT PRIMARY KEY
        data     TEXT  (JSON serializado)
        cached_at TEXT  (ISO 8601)
        ttl_hours REAL
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or CACHE_DB_PATH
        self._init_db()

    def _init_db(self) -> None:
        """Crea la base de datos y la tabla si no existen."""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            with self._connect() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS cache (
                        key       TEXT PRIMARY KEY,
                        data      TEXT NOT NULL,
                        cached_at TEXT NOT NULL,
                        ttl_hours REAL NOT NULL DEFAULT 6.0
                    )
                """)
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error inicializando base de datos de caché: {e}")

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.db_path), check_same_thread=False)

    def get(self, key: str) -> Optional[Any]:
        """Devuelve datos cacheados si están vigentes, None en caso contrario.
        
        Args:
            key: Clave de caché (ej. "la_liga_standings", "segunda_matches").
        
        Returns:
            El objeto Python original, o None si expiró o no existe.
        """
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT data, cached_at, ttl_hours FROM cache WHERE key = ?",
                    (key,)
                ).fetchone()

            if not row:
                return None

            data_json, cached_at_str, ttl_hours = row
            cached_at = datetime.fromisoformat(cached_at_str)
            expired = datetime.now() - cached_at > timedelta(hours=ttl_hours)

            if expired:
                logger.debug(f"Caché expirada para '{key}' (TTL={ttl_hours}h)")
                return None

            return json.loads(data_json)

        except (sqlite3.Error, json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Error leyendo caché para '{key}': {e}")
            return None

    def set(self, key: str, data: Any, ttl_hours: Optional[float] = None) -> bool:
        """Guarda datos en caché con un TTL.
        
        Args:
            key: Clave de caché.
            data: Objeto Python serializable a JSON.
            ttl_hours: Tiempo de vida en horas (default: CACHE_TTL_HOURS de settings).
        
        Returns:
            True si se guardó correctamente.
        """
        ttl = ttl_hours if ttl_hours is not None else CACHE_TTL_HOURS

        try:
            data_json = json.dumps(data, ensure_ascii=False, default=str)
            now_str = datetime.now().isoformat()

            with self._connect() as conn:
                conn.execute("""
                    INSERT INTO cache (key, data, cached_at, ttl_hours)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                        data      = excluded.data,
                        cached_at = excluded.cached_at,
                        ttl_hours = excluded.ttl_hours
                """, (key, data_json, now_str, ttl))
                conn.commit()

            logger.debug(f"Caché guardada para '{key}' (TTL={ttl}h)")
            return True

        except (sqlite3.Error, TypeError, ValueError) as e:
            logger.warning(f"Error guardando caché para '{key}': {e}")
            return False

    def invalidate(self, key: str) -> bool:
        """Elimina una entrada de caché manualmente."""
        try:
            with self._connect() as conn:
                conn.execute("DELETE FROM cache WHERE key = ?", (key,))
                conn.commit()
            return True
        except sqlite3.Error as e:
            logger.warning(f"Error invalidando caché para '{key}': {e}")
            return False

    def clear_expired(self) -> int:
        """Elimina todas las entradas expiradas. Devuelve el número eliminado."""
        try:
            now_str = datetime.now().isoformat()
            with self._connect() as conn:
                cursor = conn.execute("""
                    DELETE FROM cache
                    WHERE datetime(cached_at, '+' || CAST(ttl_hours AS TEXT) || ' hours')
                          < datetime(?)
                """, (now_str,))
                conn.commit()
                deleted = cursor.rowcount
            logger.info(f"Caché limpiada: {deleted} entradas eliminadas")
            return deleted
        except sqlite3.Error as e:
            logger.warning(f"Error limpiando caché expirada: {e}")
            return 0

    def stats(self) -> dict:
        """Devuelve estadísticas de uso de la caché."""
        try:
            with self._connect() as conn:
                total = conn.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
                keys = conn.execute("SELECT key, cached_at, ttl_hours FROM cache").fetchall()
            
            now = datetime.now()
            valid = sum(
                1 for _, cached_at, ttl_h in keys
                if now - datetime.fromisoformat(cached_at) < timedelta(hours=ttl_h)
            )
            return {"total_entries": total, "valid_entries": valid, "expired_entries": total - valid}
        except sqlite3.Error:
            return {"total_entries": 0, "valid_entries": 0, "expired_entries": 0}
