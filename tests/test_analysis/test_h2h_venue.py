"""Tests para el factor H2H con contexto de localía."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock
from src.analysis.factors.h2h import calculate_h2h_factor


def _make_match(home, away, result, days_ago=1):
    m = MagicMock()
    m.home_team.name = home
    m.away_team.name = away
    m.result = result
    m.date = datetime.now() - timedelta(days=days_ago)
    return m


class TestH2HVenue:
    """Verifica que el H2H tiene en cuenta si las victorias son en casa o fuera."""

    def test_positive_factor_when_home_dominates_overall(self):
        """El local que domina el H2H histórico debe tener factor positivo."""
        matches = [
            _make_match("Arsenal", "Chelsea", "1"),   # Arsenal local -> gana
            _make_match("Chelsea", "Arsenal", "2"),   # Chelsea local -> Arsenal gana de visitante
            _make_match("Arsenal", "Chelsea", "1"),
            _make_match("Arsenal", "Chelsea", "1"),
        ]
        factor = calculate_h2h_factor("Arsenal", "Chelsea", matches)
        assert factor > 0, f"Arsenal domina H2H, factor debe ser > 0, es {factor}"

    def test_venue_component_boosts_home_team(self):
        """Si el local SIEMPRE gana en casa en H2H, debe tener factor mayor."""
        # Caso A: Home gana siempre en casa
        matches_strong_home = [
            _make_match("Home", "Away", "1"),  # Home vence en casa
            _make_match("Home", "Away", "1"),
            _make_match("Away", "Home", "1"),  # Away vence en su casa (Away gana)
        ]
        # Caso B: Home gana de media pero pierde en casa
        matches_weak_home = [
            _make_match("Home", "Away", "2"),  # Away vence en el estadio de Home
            _make_match("Away", "Home", "2"),  # Home vence de visitante
            _make_match("Away", "Home", "2"),
        ]
        factor_strong = calculate_h2h_factor("Home", "Away", matches_strong_home)
        factor_weak = calculate_h2h_factor("Home", "Away", matches_weak_home)

        assert factor_strong > factor_weak, (
            f"Home más fuerte en casa debe tener mayor factor "
            f"({factor_strong:.2f} > {factor_weak:.2f})"
        )

    def test_negative_factor_when_away_dominates(self):
        """Factor negativo si el visitante domina el H2H."""
        matches = [
            _make_match("Home", "Away", "2"),   # Away gana en campo de Home
            _make_match("Away", "Home", "1"),   # Away gana en casa
            _make_match("Home", "Away", "2"),
            _make_match("Home", "Away", "2"),
        ]
        factor = calculate_h2h_factor("Home", "Away", matches)
        assert factor < 0, f"Away domina, factor debe ser < 0, es {factor}"

    def test_no_h2h_returns_zero(self):
        """Sin H2H histórico, el factor es 0."""
        matches = [_make_match("Other1", "Other2", "1")]
        factor = calculate_h2h_factor("Home", "Away", matches)
        assert factor == 0.0

    def test_draw_matches_neutral(self):
        """Los empates no penalizan ni benefician al local."""
        matches = [
            _make_match("Home", "Away", "X"),
            _make_match("Home", "Away", "X"),
            _make_match("Away", "Home", "X"),
        ]
        factor = calculate_h2h_factor("Home", "Away", matches)
        assert factor == 0.0, f"Solo empates deben dar factor 0.0, es {factor}"
