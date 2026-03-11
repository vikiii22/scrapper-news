"""Factor de exigencia competitiva del partido."""
from typing import Any, Dict, List, Optional
from src.utils.normalizers import normalize_team_name

def calculate_importance_factor(
    home_team_name: str,
    away_team_name: str,
    standings: List[Dict]
) -> float:
    """
    Calcula la diferencia de exigencia competitiva entre ambos equipos.
    Un valor positivo significa que el partido exige más al equipo local.
    """
    context = calculate_match_context(home_team_name, away_team_name, standings)
    return round(context["swing"], 2)


def calculate_match_context(
    home_team_name: str,
    away_team_name: str,
    standings: List[Dict[str, Any]],
) -> Dict[str, float]:
    """Resume urgencia, equilibrio y tensión competitiva del partido."""
    if not standings:
        return {
            "home_urgency": 0.0,
            "away_urgency": 0.0,
            "swing": 0.0,
            "tension": 0.0,
            "balance": 0.5,
        }

    home_importance = _get_team_importance(home_team_name, standings)
    away_importance = _get_team_importance(away_team_name, standings)

    position_gap = abs(home_importance["position"] - away_importance["position"])
    points_gap = abs(home_importance["points"] - away_importance["points"])
    same_race = (
        home_importance["importance_level"] == away_importance["importance_level"]
        and home_importance["importance_level"] != "midtable"
    )
    duel_bonus = 0.6 if same_race and position_gap <= 3 and points_gap <= 6 else 0.0
    balance = 1.0 - min(1.0, ((points_gap / 18.0) + (position_gap / 8.0)) / 2.0)
    tension = min(
        4.0,
        home_importance["importance_points"] + away_importance["importance_points"] + duel_bonus,
    )

    return {
        "home_urgency": round(home_importance["importance_points"], 2),
        "away_urgency": round(away_importance["importance_points"], 2),
        "swing": round(home_importance["importance_points"] - away_importance["importance_points"], 2),
        "tension": round(tension, 2),
        "balance": round(balance, 2),
    }


def _get_team_importance(team_name: str, standings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Determina la importancia del partido para un equipo según su situación real.
    """
    table = _normalize_table(standings)
    team_standing = _find_team_standing(team_name, table)

    if not team_standing:
        return {
            "importance_level": "unknown",
            "importance_points": 0.0,
            "position": 10,
            "points": 0,
        }

    position = team_standing["position"]
    points = team_standing["points"]
    total_teams = len(table)
    champions_zone = 4
    europa_zone = 6
    relegation_zone = total_teams - 3
    first_points = table[0]["points"]
    champions_cutoff = table[min(champions_zone - 1, total_teams - 1)]["points"]
    europa_cutoff = table[min(europa_zone - 1, total_teams - 1)]["points"]
    safe_cutoff_index = max(relegation_zone - 2, 0)
    safe_cutoff = table[min(safe_cutoff_index, total_teams - 1)]["points"]

    importance_points = 0.0
    importance_level = "midtable"
    title_gap = max(0, first_points - points)
    champions_gap = max(0, champions_cutoff - points)
    europa_gap = max(0, europa_cutoff - points)
    safety_gap = max(0, points - safe_cutoff)

    if position <= 3 and title_gap <= 9:
        importance_points = max(importance_points, 3.2 - (title_gap * 0.22))
        importance_level = "title_race"

    if position <= champions_zone + 2 and champions_gap <= 6:
        champions_pressure = 2.6 - (champions_gap * 0.22)
        if champions_pressure > importance_points:
            importance_points = champions_pressure
            importance_level = "champions_race"

    if position <= europa_zone + 3 and europa_gap <= 6:
        europa_pressure = 1.9 - (europa_gap * 0.18)
        if europa_pressure > importance_points:
            importance_points = europa_pressure
            importance_level = "europe_race"

    if position >= relegation_zone:
        importance_points = max(importance_points, 3.0)
        importance_level = "relegation_battle"
    elif position >= relegation_zone - 2 or safety_gap <= 4:
        relegation_pressure = 2.7 - (safety_gap * 0.25)
        if relegation_pressure > importance_points:
            importance_points = relegation_pressure
            importance_level = "relegation_battle"
    
    return {
        "importance_level": importance_level,
        "importance_points": round(max(importance_points, 0.0), 2),
        "position": position,
        "points": points,
    }


def _normalize_table(standings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normaliza la clasificación y la ordena por posición."""
    table = []
    for team in standings:
        name = normalize_team_name(team.get("team_name") or team.get("team") or "")
        if not name:
            continue
        table.append(
            {
                "team_name": name,
                "position": int(team.get("position", 10) or 10),
                "points": int(team.get("points", 0) or 0),
            }
        )
    table.sort(key=lambda entry: entry["position"])
    return table


def _find_team_standing(team_name: str, standings: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Busca un equipo en la tabla usando nombres normalizados."""
    normalized_name = normalize_team_name(team_name)
    for team in standings:
        current = team["team_name"]
        if current == normalized_name:
            return team
        if normalized_name in current or current in normalized_name:
            return team
    return None
