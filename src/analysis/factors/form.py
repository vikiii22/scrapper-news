"""Factor de racha de resultados con ponderación temporal decreciente.

Mejora sobre v1: los partidos más recientes pesan más que los antiguos.
Pesos por defecto: [0.35, 0.25, 0.20, 0.12, 0.08] (del más al menos reciente).
"""
from typing import Dict, List
from src.models.match import Match
from src.config.settings import FORM_WEIGHTS


def calculate_form_factor(
    home_team_name: str,
    away_team_name: str,
    matches: List[Match],
    last_n: int = 5
) -> float:
    """
    Calcula el factor de racha comparando la forma de ambos equipos.
    Aplica pesos decrecientes: el último partido vale ~4x más que el de hace 5 jornadas.
    """
    form_home = _calculate_team_form(home_team_name, matches, last_n)
    form_away = _calculate_team_form(away_team_name, matches, last_n)

    # Diferencia de puntos porcentuales ponderados
    diff_percentage = form_home['weighted_percentage'] - form_away['weighted_percentage']

    # El factor escala la diferencia. 100% diff -> factor de 5.
    factor = (diff_percentage / 100) * 5

    return round(factor, 2)


def _calculate_team_form(team_name: str, matches: List[Match], last_n: int) -> Dict:
    """
    Calcula la forma de un equipo aplicando pesos decrecientes por antigüedad.
    """
    team_matches = [
        m for m in matches if team_name in (m.home_team.name, m.away_team.name)
    ]

    # Ordenar: más reciente primero
    team_matches.sort(key=lambda m: m.date, reverse=True)
    last_matches = team_matches[:last_n]

    if not last_matches:
        return {
            "points": 0,
            "max_points": 0,
            "percentage_points": 0,
            "weighted_percentage": 0,
            "form_str": ""
        }

    # Usar pesos de configuración; si hay menos partidos que pesos, recortamos y renormalizamos
    weights = list(FORM_WEIGHTS[:len(last_matches)])
    weight_sum = sum(weights)
    if weight_sum > 0:
        weights = [w / weight_sum for w in weights]  # renormalizar

    # last_matches[0] es el más reciente => weights[0] es el peso mayor
    weighted_points = 0.0
    max_weighted_points = 0.0
    points = 0
    form_str = []

    for i, match in enumerate(last_matches):
        w = weights[i]
        is_win = (
            (match.home_team.name == team_name and match.result == '1') or
            (match.away_team.name == team_name and match.result == '2')
        )
        is_draw = match.result == 'X'

        if is_win:
            weighted_points += 3 * w
            points += 3
            form_str.append('V')
        elif is_draw:
            weighted_points += 1 * w
            points += 1
            form_str.append('E')
        else:
            form_str.append('D')

        max_weighted_points += 3 * w

    weighted_percentage = (
        (weighted_points / max_weighted_points) * 100
        if max_weighted_points > 0 else 0
    )
    max_points = len(last_matches) * 3
    percentage_points = (points / max_points) * 100 if max_points > 0 else 0

    # form_str: del más antiguo al más reciente (orden de lectura)
    return {
        "points": points,
        "max_points": max_points,
        "percentage_points": percentage_points,
        "weighted_percentage": weighted_percentage,
        "form_str": "".join(reversed(form_str))
    }
