"""Factor de racha contextualizado con ponderación temporal decreciente.

Además del resultado puro, pondera la dificultad del rival y el rendimiento
en el contexto de local/visitante para comparar mejor dos equipos antes de
un partido concreto.
"""
from typing import Any, Dict, List, Optional
from src.models.match import Match
from src.config.settings import FORM_WEIGHTS
from src.utils.normalizers import normalize_team_name


def calculate_form_factor(
    home_team_name: str,
    away_team_name: str,
    matches: List[Match],
    standings: Optional[List[Dict[str, Any]]] = None,
    last_n: int = 5
) -> float:
    """
    Calcula el factor de racha comparando la forma contextual de ambos equipos.
    Los partidos recientes pesan más y se ajustan por dificultad del rival.
    """
    form_home = _calculate_team_form(home_team_name, matches, last_n, standings=standings)
    form_away = _calculate_team_form(away_team_name, matches, last_n, standings=standings)
    venue_home = _calculate_team_form(
        home_team_name,
        matches,
        last_n,
        standings=standings,
        venue_filter="home",
    )
    venue_away = _calculate_team_form(
        away_team_name,
        matches,
        last_n,
        standings=standings,
        venue_filter="away",
    )

    home_index = _combine_form_indexes(form_home, venue_home)
    away_index = _combine_form_indexes(form_away, venue_away)

    diff_percentage = home_index - away_index
    momentum_diff = form_home["weighted_goal_diff"] - form_away["weighted_goal_diff"]

    factor = (diff_percentage / 100.0) * 4.5 + momentum_diff * 0.75

    return round(_clamp(factor, -5.5, 5.5), 2)


def _calculate_team_form(
    team_name: str,
    matches: List[Match],
    last_n: int,
    standings: Optional[List[Dict[str, Any]]] = None,
    venue_filter: Optional[str] = None,
) -> Dict:
    """
    Calcula la forma de un equipo aplicando pesos decrecientes por antigüedad,
    dificultad del rival y diferencia de goles.
    """
    normalized_team = normalize_team_name(team_name)
    team_matches = [
        m for m in matches
        if _match_belongs_to_team(m, normalized_team, venue_filter)
    ]

    team_matches.sort(key=lambda m: m.date, reverse=True)
    last_matches = team_matches[:last_n]
    strengths = _build_strength_map(standings or [])

    if not last_matches:
        return {
            "points": 0,
            "max_points": 0,
            "percentage_points": 0,
            "weighted_percentage": 0,
            "weighted_goal_diff": 0.0,
            "matches_analyzed": 0,
            "performance_score": 0.0,
            "form_str": ""
        }

    weights = _normalize_weights(last_matches)

    weighted_points = 0.0
    max_weighted_points = 0.0
    weighted_score = 0.0
    weighted_goal_diff = 0.0
    points = 0
    form_str = []

    for i, match in enumerate(last_matches):
        w = weights[i]
        is_home_team = normalize_team_name(match.home_team.name) == normalized_team
        scored, conceded = _extract_scores(match, is_home_team)
        goal_diff = scored - conceded
        opponent_name = (
            match.away_team.name if is_home_team else match.home_team.name
        )
        opponent_strength = strengths.get(normalize_team_name(opponent_name), 0.5)

        is_win = (
            (is_home_team and match.result == '1') or
            (not is_home_team and match.result == '2')
        )
        is_draw = match.result == 'X'
        match_points = 0

        if is_win:
            match_points = 3
            weighted_points += 3 * w
            points += 3
            form_str.append('V')
        elif is_draw:
            match_points = 1
            weighted_points += 1 * w
            points += 1
            form_str.append('E')
        else:
            form_str.append('D')

        weighted_score += _calculate_match_score(match_points, goal_diff, opponent_strength) * w
        weighted_goal_diff += goal_diff * w
        max_weighted_points += 3 * w

    weighted_percentage = weighted_score * 100
    max_points = len(last_matches) * 3
    percentage_points = (points / max_points) * 100 if max_points > 0 else 0

    return {
        "points": points,
        "max_points": max_points,
        "percentage_points": percentage_points,
        "weighted_percentage": round(weighted_percentage, 2),
        "weighted_goal_diff": round(weighted_goal_diff, 2),
        "matches_analyzed": len(last_matches),
        "performance_score": round(weighted_score, 4),
        "form_str": "".join(reversed(form_str))
    }


def _combine_form_indexes(overall_form: Dict[str, Any], venue_form: Dict[str, Any]) -> float:
    """Combina forma general y forma contextual de local/visitante."""
    overall_score = overall_form.get("weighted_percentage", 0.0)
    venue_score = venue_form.get("weighted_percentage", 0.0)
    venue_matches = venue_form.get("matches_analyzed", 0)

    if venue_matches <= 0:
        return overall_score

    venue_weight = 0.35 if venue_matches >= 3 else 0.2
    return (overall_score * (1 - venue_weight)) + (venue_score * venue_weight)


def _match_belongs_to_team(match: Match, team_name: str, venue_filter: Optional[str]) -> bool:
    """Determina si un partido pertenece al equipo y al contexto solicitado."""
    home_name = normalize_team_name(match.home_team.name)
    away_name = normalize_team_name(match.away_team.name)
    is_home = home_name == team_name
    is_away = away_name == team_name

    if not (is_home or is_away):
        return False

    if venue_filter == "home":
        return is_home
    if venue_filter == "away":
        return is_away
    return True


def _normalize_weights(matches: List[Match]) -> List[float]:
    """Recorta o extiende los pesos configurados y luego los renormaliza."""
    weights = list(FORM_WEIGHTS[:len(matches)])
    if len(weights) < len(matches):
        weights.extend([FORM_WEIGHTS[-1]] * (len(matches) - len(weights)))

    weight_sum = sum(weights)
    if weight_sum <= 0:
        return [1 / len(matches)] * len(matches)
    return [w / weight_sum for w in weights]


def _build_strength_map(standings: List[Dict[str, Any]]) -> Dict[str, float]:
    """Genera una fuerza relativa 0..1 a partir de la clasificación."""
    strength_map: Dict[str, float] = {}
    if not standings:
        return strength_map

    ratios = []
    normalized_rows = []
    for team in standings:
        team_name = normalize_team_name(team.get("team_name") or team.get("team") or "")
        if not team_name:
            continue
        matches_played = max(int(team.get("matches_played", 0) or 0), 1)
        points = float(team.get("points", 0) or 0)
        points_per_match = points / matches_played
        ratios.append(points_per_match)
        normalized_rows.append((team_name, points_per_match))

    if not ratios:
        return strength_map

    minimum = min(ratios)
    spread = max(max(ratios) - minimum, 0.01)
    for team_name, ratio in normalized_rows:
        strength_map[team_name] = (ratio - minimum) / spread

    return strength_map


def _extract_scores(match: Match, is_home_team: bool) -> tuple:
    """Extrae goles anotados/encajados; si faltan, infiere un margen mínimo."""
    home_score = getattr(match, "home_score", None)
    away_score = getattr(match, "away_score", None)
    if isinstance(home_score, int) and isinstance(away_score, int):
        if is_home_team:
            return home_score, away_score
        return away_score, home_score

    if match.result == "X":
        return 0, 0
    if (is_home_team and match.result == "1") or (not is_home_team and match.result == "2"):
        return 1, 0
    return 0, 1


def _calculate_match_score(points: int, goal_diff: int, opponent_strength: float) -> float:
    """Valora un partido reciente en escala 0..1."""
    result_score = points / 3.0
    goal_component = _clamp(goal_diff / 3.0, -1.0, 1.0) * 0.18
    opponent_delta = opponent_strength - 0.5

    if points == 3:
        result_score += opponent_delta * 0.22
    elif points == 1:
        result_score += opponent_delta * 0.10
    else:
        result_score += opponent_delta * 0.05
        result_score -= (0.5 - opponent_strength) * 0.18

    return _clamp(result_score + goal_component, 0.0, 1.0)


def _clamp(value: float, minimum: float, maximum: float) -> float:
    """Limita un valor a un rango."""
    return max(min(value, maximum), minimum)
