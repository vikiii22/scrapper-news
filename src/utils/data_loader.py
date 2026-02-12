"""Utilidades para cargar y normalizar datos."""
import json
from pathlib import Path
from typing import Any, Dict, List

def load_json_data(file_path: Path) -> Any:
    """Carga datos desde un archivo JSON."""
    if not file_path.exists():
        return None
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json_data(data: Any, file_path: Path):
    """Guarda datos en un archivo JSON."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
