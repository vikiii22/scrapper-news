"""
BBDD local en JSON.

Guarda todo lo que se descarga en tiempo real para ir construyendo
un histórico propio y no depender siempre de internet:

    data/db/
        teams.json        -> un registro por equipo (forma, goles, fixtures, noticias)
        h2h.json          -> caché de enfrentamientos directos
        predictions.json  -> log de pronósticos generados

Uso:
    from .database import get_team, save_team, log_prediction, stats
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
DB_DIR = BASE_DIR / "data" / "db"
TEAMS_FILE = DB_DIR / "teams.json"
H2H_FILE = DB_DIR / "h2h.json"
PREDICTIONS_FILE = DB_DIR / "predictions.json"
QUINIELA_FILE = DB_DIR / "quiniela.json"


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


# ---------------------------------------------------------------------------
# Teams
# ---------------------------------------------------------------------------

def get_team(team_name: str, max_age_hours: Optional[float] = None) -> Optional[Dict[str, Any]]:
    """Devuelve el registro guardado de un equipo, o None si no existe / está caducado."""
    teams = _read_json(TEAMS_FILE, {})
    key = normalize(team_name)
    rec = teams.get(key)
    if not rec:
        # búsqueda difusa: contiene / contenido
        for k, v in teams.items():
            if key in k or k in key:
                rec = v
                break
    if not rec:
        return None
    if max_age_hours is not None:
        try:
            ts = datetime.fromisoformat(rec.get("fetched_at", "1970-01-01"))
            age_h = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
            if age_h > max_age_hours:
                return None
        except Exception:
            return None
    return rec


def save_team(record: Dict[str, Any]) -> Dict[str, Any]:
    """Guarda/actualiza el registro de un equipo. Añade fetched_at si falta."""
    teams = _read_json(TEAMS_FILE, {})
    record = dict(record)
    record.setdefault("fetched_at", _now_iso())
    record["updated_at"] = _now_iso()
    # histórico de forma: acumulamos snapshots de "recent"
    key = normalize(record.get("name", "unknown"))
    prev = teams.get(key, {})
    history: List[Dict[str, Any]] = prev.get("history", [])
    if record.get("recent") and (not history or history[-1].get("recent") != record["recent"]):
        history.append({"at": record["fetched_at"], "recent": record["recent"]})
        history = history[-20:]  # conservamos últimos 20
    record["history"] = history
    teams[key] = record
    _write_json(TEAMS_FILE, teams)
    return record


def list_teams() -> List[Dict[str, Any]]:
    return list(_read_json(TEAMS_FILE, {}).values())


# ---------------------------------------------------------------------------
# H2H
# ---------------------------------------------------------------------------

def _h2h_key(a: str, b: str) -> str:
    x, y = sorted([normalize(a), normalize(b)])
    return f"{x}||{y}"


def get_h2h(team_a: str, team_b: str) -> Optional[List]:
    h2h = _read_json(H2H_FILE, {})
    rec = h2h.get(_h2h_key(team_a, team_b))
    if not rec:
        return None
    return rec.get("matches")


def save_h2h(team_a: str, team_b: str, matches: List, source: str = "") -> None:
    h2h = _read_json(H2H_FILE, {})
    h2h[_h2h_key(team_a, team_b)] = {
        "teams": [team_a, team_b],
        "matches": matches,
        "source": source,
        "fetched_at": _now_iso(),
    }
    _write_json(H2H_FILE, h2h)


# ---------------------------------------------------------------------------
# Predictions log
# ---------------------------------------------------------------------------

def log_prediction(result: Dict[str, Any]) -> None:
    preds = _read_json(PREDICTIONS_FILE, [])
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
    }
    preds.append(entry)
    preds = preds[-500:]  # tope para no crecer sin límite
    _write_json(PREDICTIONS_FILE, preds)


def stats() -> Dict[str, Any]:
    return {
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
    """Guarda el análisis de una jornada. Devuelve la entrada guardada."""
    all_q = _read_json(QUINIELA_FILE, {})
    key = str(jornada or "sin-numero")
    entry = {"jornada": jornada, "analyzed_at": _now_iso(), "matches": analysis}
    all_q[key] = entry
    _write_json(QUINIELA_FILE, all_q)
    return entry


def list_quinielas() -> List[Any]:
    return sorted(_read_json(QUINIELA_FILE, {}).keys())


def get_quiniela(jornada) -> Optional[Dict[str, Any]]:
    return _read_json(QUINIELA_FILE, {}).get(str(jornada))
