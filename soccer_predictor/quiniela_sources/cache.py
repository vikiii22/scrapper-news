"""Caché JSON en disco para las fuentes de la jornada."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional


class Cache:
    """Caché simple por fichero, con caducidad. Nunca lanza."""

    def __init__(self, root: Path, max_age_hours: float = 6.0):
        self.root = Path(root)
        self.max_age_hours = max_age_hours
        try:
            self.root.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    def _path(self, key: str) -> Path:
        digest = hashlib.sha1(key.encode("utf-8")).hexdigest()
        return self.root / f"{digest}.json"

    def get(self, key: str) -> Optional[Any]:
        try:
            data = json.loads(self._path(key).read_text(encoding="utf-8"))
            saved = datetime.fromisoformat(data["saved_at"])
            if saved.tzinfo is None:
                saved = saved.replace(tzinfo=timezone.utc)
            age = datetime.now(timezone.utc) - saved
            if age > timedelta(hours=self.max_age_hours):
                return None
            return data.get("value")
        except Exception:
            return None

    def set(self, key: str, value: Any) -> None:
        try:
            payload = {
                "key": key,
                "saved_at": datetime.now(timezone.utc).isoformat(),
                "value": value,
            }
            self._path(key).write_text(
                json.dumps(payload, ensure_ascii=False), encoding="utf-8"
            )
        except Exception:
            pass
