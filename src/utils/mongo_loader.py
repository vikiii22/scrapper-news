"""Utilidades para cargar y guardar datos en MongoDB en vez de JSON."""
from pymongo import MongoClient
from typing import Any, Dict, List, Optional
import os

# Configuración MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb://root:Events_root@212.227.110.211:27021/")
MONGO_DB = os.getenv("MONGO_DB", "FutbolAnalisis")

client = MongoClient(MONGO_URI)
db = client[MONGO_DB]

def load_mongo_data(collection_name: str, query: Optional[Dict] = None) -> List[Dict]:
    """Carga datos desde una colección de MongoDB."""
    query = query or {}
    collection = db[collection_name]
    return list(collection.find(query, {"_id": 0}))

def save_mongo_data(collection_name: str, data: Any):
    """Guarda datos en una colección de MongoDB. Reemplaza los documentos existentes."""
    collection = db[collection_name]
    if isinstance(data, list):
        collection.delete_many({})
        if data:
            collection.insert_many(data)
    elif isinstance(data, dict):
        collection.replace_one({}, data, upsert=True)
    else:
        raise ValueError("Los datos deben ser una lista o un diccionario.")
