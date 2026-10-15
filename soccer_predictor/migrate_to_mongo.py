"""
Migra data/db/*.json -> MongoDB. Idempotente (upserts, no duplica teams/h2h/quinielas).

Uso:
    # con .env (MONGO_URI=...):
    python -m soccer_predictor.migrate_to_mongo
    # o pasando la URI:
    python -m soccer_predictor.migrate_to_mongo "mongodb://root:...@host:27018/?authSource=admin"
    # dry-run (solo cuenta, no escribe):
    python -m soccer_predictor.migrate_to_mongo --dry-run
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent.parent
DB_DIR = BASE_DIR / "data" / "db"


def _load(name, default):
    p = DB_DIR / name
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"! No se pudo leer {name}: {e}")
        return default


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    dry = any(a in ("--dry-run", "-n") for a in sys.argv[1:])
    uri = args[0] if args else (os.getenv("MONGO_URI") or os.getenv("MONGODB_URI") or "")
    if not uri:
        print("Falta MONGO_URI. Ponlo en .env o pásalo como argumento.")
        print('  python -m soccer_predictor.migrate_to_mongo "mongodb://..."')
        return 2
    db_name = os.getenv("MONGO_DB", "soccer_predictor")

    teams = _load("teams.json", {})
    h2h = _load("h2h.json", {})
    preds = _load("predictions.json", [])
    quinis = _load("quiniela.json", {})
    print(f"JSON local: {len(teams)} teams, {len(h2h)} h2h, {len(preds)} predictions, {len(quinis)} quinielas")

    if dry:
        print("(dry-run, no se escribe nada)")
        return 0

    from pymongo import MongoClient

    client = MongoClient(uri, serverSelectionTimeoutMS=8000)
    client.admin.command("ping")
    db = client[db_name]

    # --- teams ---
    n_teams = 0
    for key, rec in teams.items():
        doc = dict(rec)
        doc["_id"] = key
        db["teams"].replace_one({"_id": key}, doc, upsert=True)
        n_teams += 1
    # --- h2h ---
    n_h2h = 0
    for key, rec in h2h.items():
        doc = dict(rec)
        doc["_id"] = key
        db["h2h"].replace_one({"_id": key}, doc, upsert=True)
        n_h2h += 1
    # --- predictions (log: insertar las que falten por 'at'+teams) ---
    n_preds = 0
    for entry in preds:
        q = {"at": entry.get("at"), "teams": entry.get("teams"),
             "prediction_1x2": entry.get("prediction_1x2")}
        if db["predictions"].find_one(q):
            continue
        db["predictions"].insert_one(dict(entry))
        n_preds += 1
    # --- quinielas ---
    n_q = 0
    for key, rec in quinis.items():
        doc = dict(rec)
        doc["_id"] = str(key)
        db["quinielas"].replace_one({"_id": str(key)}, doc, upsert=True)
        n_q += 1

    print(f"Mongo '{db_name}': {n_teams} teams upsert, {n_h2h} h2h upsert, "
          f"{n_preds} predictions nuevas, {n_q} quinielas upsert")
    print("Totales en Mongo:",
          db["teams"].count_documents({}),
          db["h2h"].count_documents({}),
          db["predictions"].count_documents({}),
          db["quinielas"].count_documents({}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
