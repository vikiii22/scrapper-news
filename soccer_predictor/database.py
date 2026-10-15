"""
BBDD con backend dual: MongoDB (principal si hay MONGO_URI) + JSON (fallback).

Colecciones Mongo (db por defecto: soccer_predictor):
    teams        -> _id = nombre normalizado, un doc por equipo
    h2h          -> _id = "a||b" ordenado y normalizado
    predictions  -> un doc por pronóstico (log)
    quinielas    -> _id = str(jornada)

Config (.env o variables de entorno):
    MONGO_URI=mongodb://root:...@212.227.110.211:27018/?authSource=admin
    MONGO_DB=soccer_predictor   (opcional)

Si no hay MONGO_URI, o pymongo no está instalado, o Mongo no responde,
todo sigue funcionando con los JSON de data/db/ como antes.

Uso:
    from .database import get_team, save_team, log_prediction, stats
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent.parent
DB_DIR = BASE_DIR / "data" / "db"
TEAMS_FILE = DB_DIR / "teams.json"
H2H_FILE = DB_DIR / "h2h.json"
PREDICTIONS_FILE = DB_DIR / "predictions.json"
QUINIELA_FILE = DB_DIR / "quiniela.json"

MONGO_URI = os.getenv("MONGO_URI") or os.getenv("MONGODB_URI") or ""
MONGO_DB = os.getenv("MONGO_DB", "soccer_predictor")

_mongo_db = None
_mongo_tried = False


def backend() -> str:
    """'mongo' si hay conexión utilizable, si no 'json'."""
    return "mongo" if _get_mongo() is not None else "json"


def _get_mongo():
    """Devuelve la base Mongo o None (lazy, con caché, nunca lanza)."""
    global _mongo_db, _mongo_tried, MONGO_URI, MONGO_DB
    # Releer env por si se fijó después del import (tests, migración)
    if not MONGO_URI:
        MONGO_URI = os.getenv("MONGO_URI") or os.getenv("MONGODB_URI") or ""
    if not MONGO_URI:
        return None
    if _mongo_db is not None:
        return _mongo_db
    if _mongo_tried:
        # Reintentamos igualmente cada vez que se pide (por si Mongo
        # arrancó después), pero sin romper nada si falla.
        pass
    _mongo_tried = True
    try:
        from pymongo import MongoClient

        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        _mongo_db = client[os.getenv("MONGO_DB", MONGO_DB) or "soccer_predictor"]
        # Índices (mejor esfuerzo, una sola vez)
        try:
            _mongo_db["teams"].create_index("updated_at")
            _mongo_db["h2h"].create_index("fetched_at")
            _mongo_db["predictions"].create_index("at")
        except Exception:
            pass
        return _mongo_db
    except Exception:
        return None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_db() -> None:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    for f in (TEAMS_FILE, H2H_FILE, QUINIELA_FILE):
        if not f.exists():
            f.write_text(json.dumps({}, ensure_ascii=False, indent=2), encoding="utf-8")
    if not PREDICTIONS_FILE.exists():
        PREDICTIONS_FILE.write_text(json.dumps([], ensure_ascii=False, indent=2), encoding="utf-8")


def _read_json(path: Path, default):
    _ensure_db()
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json(path: Path, data) -> None:
    _ensure_db()
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def normalize(name: str) -> str:
    return " ".join(name.strip().lower().split())


def _parse_age_ok(rec: Dict[str, Any], max_age_hours: Optional[float]) -> bool:
    if max_age_hours is None:
        return True
    try:
        ts = datetime.fromisoformat(rec.get("fetched_at", "1970-01-01"))
        age_h = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
        return age_h <= max_age_hours
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Teams
# ---------------------------------------------------------------------------

def get_team(team_name: str, max_age_hours: Optional[float] = None) -> Optional[Dict[str, Any]]:
    """Devuelve el registro guardado de un equipo, o None si no existe / está caducado."""
    key = normalize(team_name)
    mdb = _get_mongo()
    if mdb is not None:
        try:
            rec = mdb["teams"].find_one({"_id": key})
            if not rec:
                # búsqueda difusa equivalente a la JSON: contiene / contenido
                # (nº equipos pequeño: escaneo de _id + name, sin regex costosas)
                for doc in mdb["teams"].find({}, {"_id": 1, "name": 1}):
                    k = doc.get("_id", "")
                    if key in k or k in key:
                        rec = mdb["teams"].find_one({"_id": k})
                        break
            if not rec:
                return None
            rec.pop("_key", None)
            if not _parse_age_ok(rec, max_age_hours):
                return None
            return rec
        except Exception:
            pass  # cae al JSON
    # --- fallback JSON ---
    teams = _read_json(TEAMS_FILE, {})
    rec = teams.get(key)
    if not rec:
        for k, v in teams.items():
            if key in k or k in key:
                rec = v
                break
    if not rec:
        return None
    if not _parse_age_ok(rec, max_age_hours):
        return None
    return rec


def save_team(record: Dict[str, Any]) -> Dict[str, Any]:
    """Guarda/actualiza el registro de un equipo. Añade fetched_at si falta."""
    record = dict(record)
    record.setdefault("fetched_at", _now_iso())
    record["updated_at"] = _now_iso()
    key = normalize(record.get("name", "unknown"))

    mdb = _get_mongo()
    if mdb is not None:
        try:
            prev = mdb["teams"].find_one({"_id": key}) or {}
            history: List[Dict[str, Any]] = prev.get("history", [])
            if record.get("recent") and (not history or history[-1].get("recent") != record["recent"]):
                history.append({"at": record["fetched_at"], "recent": record["recent"]})
                history = history[-20:]
            record["history"] = history
            doc = dict(record)
            doc["_id"] = key
            mdb["teams"].replace_one({"_id": key}, doc, upsert=True)
            # Espejo JSON (mejor esfuerzo, para backup/offline)
            try:
                _mirror_team_json(key, record)
            except Exception:
                pass
            return record
        except Exception:
            pass  # cae al JSON
    # --- fallback JSON ---
    teams = _read_json(TEAMS_FILE, {})
    prev = teams.get(key, {})
    history = prev.get("history", [])
    if record.get("recent") and (not history or history[-1].get("recent") != record["recent"]):
        history.append({"at": record["fetched_at"], "recent": record["recent"]})
        history = history[-20:]
    record["history"] = history
    teams[key] = record
    _write_json(TEAMS_FILE, teams)
    return record


def _mirror_team_json(key: str, record: Dict[str, Any]) -> None:
    teams = _read_json(TEAMS_FILE, {})
    teams[key] = record
    _write_json(TEAMS_FILE, teams)


def list_teams() -> List[Dict[str, Any]]:
    mdb = _get_mongo()
    if mdb is not None:
        try:
            return list(mdb["teams"].find({}))
        except Exception:
            pass
    return list(_read_json(TEAMS_FILE, {}).values())


# ---------------------------------------------------------------------------
# H2H
# ---------------------------------------------------------------------------

def _h2h_key(a: str, b: str) -> str:
    x, y = sorted([normalize(a), normalize(b)])
    return f"{x}||{y}"


def get_h2h(team_a: str, team_b: str) -> Optional[List]:
    mdb = _get_mongo()
    if mdb is not None:
        try:
            rec = mdb["h2h"].find_one({"_id": _h2h_key(team_a, team_b)})
            if rec:
                return rec.get("matches")
        except Exception:
            pass
    h2h = _read_json(H2H_FILE, {})
    rec = h2h.get(_h2h_key(team_a, team_b))
    if not rec:
        return None
    return rec.get("matches")


def save_h2h(team_a: str, team_b: str, matches: List, source: str = "") -> None:
    key = _h2h_key(team_a, team_b)
    mdb = _get_mongo()
    if mdb is not None:
        try:
            mdb["h2h"].replace_one(
                {"_id": key},
                {"_id": key, "teams": [team_a, team_b], "matches": matches,
                 "source": source, "fetched_at": _now_iso()},
                upsert=True,
            )
        except Exception:
            pass
    # Siempre espejo JSON (backup barato)
    try:
        h2h = _read_json(H2H_FILE, {})
        h2h[key] = {"teams": [team_a, team_b], "matches": matches,
                    "source": source, "fetched_at": _now_iso()}
        _write_json(H2H_FILE, h2h)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Predictions log
# ---------------------------------------------------------------------------

def log_prediction(result: Dict[str, Any]) -> None:
    entry = {
        "at": _now_iso(),
        "teams": result.get("teams"),
        "competition": result.get("competition"),
        "date": result.get("date"),
        "prediction_1x2": result.get("prediction_1x2"),
        "prob_1x2": result.get("prob_1x2"),
        "over_under": result.get("over_under"),
        "both_teams_score": result.get("both_teams_score"),
        "expected_goals": result.get("expected_goals"),
        "data_sources": result.get("data_sources"),
        "player_context": result.get("player_context"),
        "absences": result.get("absences"),
        "player_adjustments": result.get("player_adjustments"),
        "positions": result.get("positions"),
        "normalization": result.get("normalization"),
        "low_confidence": result.get("low_confidence", False),
    }
    mdb = _get_mongo()
    if mdb is not None:
        try:
            mdb["predictions"].insert_one(dict(entry))
        except Exception:
            pass
    # Espejo JSON con tope de 500 (el JSON no debe crecer sin límite)
    try:
        preds = _read_json(PREDICTIONS_FILE, [])
        preds.append(entry)
        preds = preds[-500:]
        _write_json(PREDICTIONS_FILE, preds)
    except Exception:
        pass


def stats() -> Dict[str, Any]:
    mdb = _get_mongo()
    if mdb is not None:
        try:
            return {
                "backend": "mongo",
                "db": mdb.name,
                "teams": mdb["teams"].count_documents({}),
                "h2h_pairs": mdb["h2h"].count_documents({}),
                "predictions": mdb["predictions"].count_documents({}),
                "quinielas": mdb["quinielas"].count_documents({}),
                "db_dir": str(DB_DIR),
            }
        except Exception:
            pass
    return {
        "backend": "json",
        "teams": len(_read_json(TEAMS_FILE, {})),
        "h2h_pairs": len(_read_json(H2H_FILE, {})),
        "predictions": len(_read_json(PREDICTIONS_FILE, [])),
        "quinielas": len(_read_json(QUINIELA_FILE, {})),
        "db_dir": str(DB_DIR),
    }


# ---------------------------------------------------------------------------
# Quinielas (boletos LAE analizados)
# ---------------------------------------------------------------------------

def save_quiniela(jornada, analysis: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Guarda el análisis de una jornada COMO NUEVA VERSIÓN (nunca borra)."""
    try:
        from .prediction_engine import ENGINE_VERSION
    except ImportError:
        try:
            from prediction_engine import ENGINE_VERSION
        except ImportError:
            ENGINE_VERSION = "?"
    key = str(jornada or "sin-numero")

    mdb = _get_mongo()
    if mdb is not None:
        try:
            prev = mdb["quinielas"].find_one({"_id": key}) or {}
            versions = prev.get("versions", [])
            versions.append({"analyzed_at": _now_iso(), "engine": ENGINE_VERSION,
                             "n_matches": len(analysis)})
            entry = {"_id": key, "jornada": jornada, "analyzed_at": _now_iso(),
                     "matches": analysis, "versions": versions[-10:],
                     "actuals": prev.get("actuals", {}), "played": prev.get("played", {})}
            if entry["actuals"]:
                try:
                    try:
                        from .quiniela import score_analysis
                    except ImportError:
                        from quiniela import score_analysis
                    entry["score"] = score_analysis(analysis, entry["actuals"], entry.get("played"))
                    entry["scored_at"] = _now_iso()
                except Exception:
                    if prev.get("score"):
                        entry["score"] = prev.get("score")
            elif prev.get("score") and not entry.get("actuals"):
                pass
            mdb["quinielas"].replace_one({"_id": key}, entry, upsert=True)
            try:
                _mirror_quiniela_json(key, entry)
            except Exception:
                pass
            return entry
        except Exception:
            pass  # cae al JSON
    # --- fallback JSON ---
    all_q = _read_json(QUINIELA_FILE, {})
    prev = all_q.get(key, {})
    versions = prev.get("versions", [])
    versions.append({"analyzed_at": _now_iso(), "engine": ENGINE_VERSION,
                     "n_matches": len(analysis)})
    entry = {"jornada": jornada, "analyzed_at": _now_iso(), "matches": analysis,
             "versions": versions[-10:],
             "actuals": prev.get("actuals", {}),
             "played": prev.get("played", {})}
    if entry["actuals"]:
        try:
            try:
                from .quiniela import score_analysis
            except ImportError:
                from quiniela import score_analysis
            entry["score"] = score_analysis(analysis, entry["actuals"],
                                            entry.get("played"))
            entry["scored_at"] = _now_iso()
        except Exception:
            if prev.get("score"):
                entry["score"] = prev.get("score")
    all_q[key] = entry
    _write_json(QUINIELA_FILE, all_q)
    return entry


def _mirror_quiniela_json(key: str, entry: Dict[str, Any]) -> None:
    all_q = _read_json(QUINIELA_FILE, {})
    e = dict(entry)
    e.pop("_id", None)
    all_q[key] = e
    _write_json(QUINIELA_FILE, all_q)


def save_played(jornada, played: Dict[Any, str]) -> Optional[Dict[str, Any]]:
    clean = {str(k): v for k, v in played.items() if v in ("1", "X", "2")}
    mdb = _get_mongo()
    if mdb is not None:
        try:
            entry = mdb["quinielas"].find_one({"_id": str(jornada)})
            if entry is not None:
                entry["played"] = clean
                mdb["quinielas"].replace_one({"_id": str(jornada)}, entry)
                try:
                    _mirror_quiniela_json(str(jornada), entry)
                except Exception:
                    pass
                return entry
        except Exception:
            pass
    all_q = _read_json(QUINIELA_FILE, {})
    entry = all_q.get(str(jornada))
    if not entry:
        return None
    entry["played"] = clean
    all_q[str(jornada)] = entry
    _write_json(QUINIELA_FILE, all_q)
    return entry


def list_quinielas() -> List[Any]:
    mdb = _get_mongo()
    if mdb is not None:
        try:
            return sorted(d["_id"] for d in mdb["quinielas"].find({}, {"_id": 1}))
        except Exception:
            pass
    return sorted(_read_json(QUINIELA_FILE, {}).keys())


def get_quiniela(jornada) -> Optional[Dict[str, Any]]:
    mdb = _get_mongo()
    if mdb is not None:
        try:
            return mdb["quinielas"].find_one({"_id": str(jornada)})
        except Exception:
            pass
    return _read_json(QUINIELA_FILE, {}).get(str(jornada))


def save_quiniela_results(jornada, actuals: Dict[Any, Dict[str, Any]],
                          score: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Guarda los resultados reales y el acierto de una jornada."""
    mdb = _get_mongo()
    if mdb is not None:
        try:
            entry = mdb["quinielas"].find_one({"_id": str(jornada)})
            if entry is not None:
                entry["actuals"] = {str(k): v for k, v in actuals.items()}
                entry["score"] = score
                entry["scored_at"] = _now_iso()
                mdb["quinielas"].replace_one({"_id": str(jornada)}, entry)
                try:
                    _mirror_quiniela_json(str(jornada), entry)
                except Exception:
                    pass
                return entry
        except Exception:
            pass
    all_q = _read_json(QUINIELA_FILE, {})
    entry = all_q.get(str(jornada))
    if not entry:
        return None
    entry["actuals"] = {str(k): v for k, v in actuals.items()}
    entry["score"] = score
    entry["scored_at"] = _now_iso()
    all_q[str(jornada)] = entry
    _write_json(QUINIELA_FILE, all_q)
    return entry
