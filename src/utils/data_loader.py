"""Utilidades para cargar y guardar datos usando MongoDB en vez de JSON."""
from pathlib import Path
from typing import Any, Dict, List
from .mongo_loader import load_mongo_data, save_mongo_data

def _json_name_from_path(file_path: Path) -> str:
    """Obtiene el nombre base del archivo JSON para usar como colección."""
    return file_path.stem

def load_json_data(file_path: Path) -> Any:
    """Carga datos desde MongoDB usando el nombre del archivo como colección."""
    collection = _json_name_from_path(file_path)
    data = load_mongo_data(collection)
    return data if data else None

def save_json_data(data: Any, file_path: Path):
    """Guarda datos en MongoDB usando el nombre del archivo como colección."""
    collection = _json_name_from_path(file_path)
    save_mongo_data(collection, data)
