"""Tests para el factor de forma con ponderación temporal decreciente."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock
from src.analysis.factors.form import calculate_form_factor, _calculate_team_form


def _make_match(home, away, result, days_ago):
    """Helper para crear partidos simulados."""
    m = MagicMock()
    m.home_team.name = home
    m.away_team.name = away
    m.result = result
    m.date = datetime.now() - timedelta(days=days_ago)
    return m


class TestFormWeighted:
    """Verifica que la ponderación temporal funciona correctamente."""

    def test_recent_win_more_valuable_than_old_win(self):
        """Equipo A ganó ayer; equipo B ganó hace 5 semanas. A debe tener mejor forma."""
        team_a_matches = [
            _make_match("A", "X", "1", days_ago=1),   # Victoria ayer (peso 0.35)
            _make_match("A", "X", "2", days_ago=8),   # Derrota
            _make_match("A", "X", "2", days_ago=15),  # Derrota
            _make_match("A", "X", "2", days_ago=22),  # Derrota
            _make_match("A", "X", "2", days_ago=29),  # Derrota
        ]
        team_b_matches = [
            _make_match("B", "Y", "2", days_ago=1),   # Derrota ayer
            _make_match("B", "Y", "2", days_ago=8),
            _make_match("B", "Y", "2", days_ago=15),
            _make_match("B", "Y", "2", days_ago=22),
            _make_match("B", "Y", "1", days_ago=29),  # Victoria antigua (peso 0.08)
        ]
        all_matches = team_a_matches + team_b_matches

        form_a = _calculate_team_form("A", all_matches, 5)
        form_b = _calculate_team_form("B", all_matches, 5)

        # A ganó recientemente; tiene mayor weighted_percentage
        assert form_a["weighted_percentage"] > form_b["weighted_percentage"], (
            f"A (victoria reciente) debería tener más forma que B (victoria en el pasado). "
            f"A={form_a['weighted_percentage']:.2f}, B={form_b['weighted_percentage']:.2f}"
        )

    def test_weights_sum_to_one(self):
        """Los pesos deben sumar 1 (o a 1 tras renormalización)."""
        from src.config.settings import FORM_WEIGHTS
        assert abs(sum(FORM_WEIGHTS) - 1.0) < 1e-9, \
            f"FORM_WEIGHTS debe sumar 1.0, suma {sum(FORM_WEIGHTS)}"

    def test_form_factor_positive_when_home_better(self):
        """Factor positivo si el local viene de mejor forma."""
        matches = [
            # Local ganó los 5 últimos
            _make_match("Home", "Opp1", "1", days_ago=3),
            _make_match("Home", "Opp2", "1", days_ago=10),
            _make_match("Home", "Opp3", "1", days_ago=17),
            _make_match("Home", "Opp4", "1", days_ago=24),
            _make_match("Home", "Opp5", "1", days_ago=31),
            # Visitante perdió los 5 últimos
            _make_match("Away", "Opp1", "2", days_ago=3),
            _make_match("Away", "Opp2", "2", days_ago=10),
            _make_match("Away", "Opp3", "2", days_ago=17),
            _make_match("Away", "Opp4", "2", days_ago=24),
            _make_match("Away", "Opp5", "2", days_ago=31),
        ]
        factor = calculate_form_factor("Home", "Away", matches)
        assert factor > 0, f"Factor debería ser positivo, es {factor}"

    def test_empty_matches_returns_zero(self):
        """Sin historial, el factor debe ser 0."""
        factor = calculate_form_factor("TeamA", "TeamB", [])
        assert factor == 0.0
