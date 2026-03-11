"""Tests para comparación contextual entre equipos."""
from datetime import datetime, timedelta

from src.analysis.factors.importance import calculate_match_context
from src.analysis.predictor import PredictionEngine
from src.models.match import Match, MatchStatus, Team


def _make_match(match_id, home, away, home_score, away_score, days_ago):
    return Match(
        id=match_id,
        home_team=Team(id=match_id * 10 + 1, name=home),
        away_team=Team(id=match_id * 10 + 2, name=away),
        date=datetime.now() - timedelta(days=days_ago),
        league="La Liga",
        status=MatchStatus.FINISHED,
        home_score=home_score,
        away_score=away_score,
    )


def test_lambda_changes_with_opponent_defense():
    historical_matches = [
        _make_match(1, "Attackers", "Opponent A", 3, 1, 3),
        _make_match(2, "Attackers", "Opponent B", 2, 0, 10),
        _make_match(3, "Opponent C", "Attackers", 1, 2, 17),
        _make_match(4, "Attackers", "Opponent D", 2, 1, 24),
        _make_match(5, "Opponent E", "Attackers", 0, 1, 31),
        _make_match(6, "Weak Defense", "Other", 1, 3, 2),
        _make_match(7, "Other", "Weak Defense", 2, 0, 9),
        _make_match(8, "Weak Defense", "Other", 0, 2, 16),
        _make_match(9, "Other", "Weak Defense", 3, 1, 23),
        _make_match(10, "Weak Defense", "Other", 1, 2, 30),
        _make_match(11, "Strong Defense", "Other", 1, 0, 2),
        _make_match(12, "Other", "Strong Defense", 0, 1, 9),
        _make_match(13, "Strong Defense", "Other", 1, 0, 16),
        _make_match(14, "Other", "Strong Defense", 0, 0, 23),
        _make_match(15, "Strong Defense", "Other", 2, 1, 30),
    ]
    engine = PredictionEngine(historical_matches=historical_matches, standings=[])

    lambda_vs_weak = engine._calculate_lambda("Attackers", "Weak Defense", True, False)
    lambda_vs_strong = engine._calculate_lambda("Attackers", "Strong Defense", True, False)

    assert lambda_vs_weak > lambda_vs_strong, (
        "El mismo equipo debe proyectar más goles ante una defensa frágil que ante una sólida. "
        f"weak={lambda_vs_weak:.2f}, strong={lambda_vs_strong:.2f}"
    )


def test_draw_adjustment_rewards_balanced_matches():
    engine = PredictionEngine(historical_matches=[], standings=[])

    close_adjustment = engine._calculate_draw_adjustment(
        {
            "standings": 0.2,
            "form": 0.15,
            "players": 0.0,
            "h2h": 0.1,
            "home_away": 0.2,
            "away_performance": 0.15,
            "importance_tension": 2.8,
        }
    )
    uneven_adjustment = engine._calculate_draw_adjustment(
        {
            "standings": 3.2,
            "form": 2.6,
            "players": 0.9,
            "h2h": 1.8,
            "home_away": 2.1,
            "away_performance": 0.4,
            "importance_tension": 1.5,
        }
    )

    assert close_adjustment > 0, "Un duelo equilibrado debe subir la probabilidad de empate"
    assert uneven_adjustment < 0, "Un duelo desequilibrado debe bajar la probabilidad de empate"


def test_match_context_detects_high_tension_relegation_duel():
    standings = [
        {"position": 1, "team_name": "Leader", "points": 60},
        {"position": 2, "team_name": "Runner Up", "points": 55},
        {"position": 3, "team_name": "Third", "points": 50},
        {"position": 4, "team_name": "Fourth", "points": 45},
        {"position": 5, "team_name": "Fifth", "points": 40},
        {"position": 6, "team_name": "Sixth", "points": 36},
        {"position": 7, "team_name": "Safe", "points": 31},
        {"position": 8, "team_name": "Home", "points": 28},
        {"position": 9, "team_name": "Away", "points": 27},
        {"position": 10, "team_name": "Bottom", "points": 22},
    ]

    context = calculate_match_context("Home", "Away", standings)

    assert context["tension"] >= 3.5, f"Se esperaba alta tensión competitiva, obtuvo {context['tension']}"
    assert context["balance"] >= 0.8, f"Duelo parejo debe tener balance alto, obtuvo {context['balance']}"