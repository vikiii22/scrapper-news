"""Tests para el factor de cuotas de mercado."""
import pytest
from src.analysis.factors.odds_factor import calculate_odds_factor, blend_with_model


class TestOddsFactor:
    """Tests para conversión de cuotas y mezcla con modelo."""

    VALID_ODDS = {"1": 1.45, "X": 4.20, "2": 6.50}
    EXPECTED_TOTAL_PROB = 100.0

    def test_probabilities_sum_to_100(self):
        """Las probabilidades normalizadas deben sumar 100%."""
        result = calculate_odds_factor(self.VALID_ODDS)
        assert result["valid"] is True
        total = result["prob_1"] + result["prob_X"] + result["prob_2"]
        assert abs(total - 100.0) < 0.2, f"Deben sumar 100, suman {total}"

    def test_favorite_has_highest_probability(self):
        """El equipo con la cuota más baja debe tener el % más alto."""
        result = calculate_odds_factor(self.VALID_ODDS)
        # Cuota 1.45 es la más baja (favorito = local)
        assert result["prob_1"] > result["prob_X"] > result["prob_2"]

    def test_overround_is_positive(self):
        """El overround de la casa debe ser positivo (es su margen de beneficio)."""
        result = calculate_odds_factor(self.VALID_ODDS)
        assert result["overround"] > 0, "El overround siempre es positivo"

    def test_fair_odds_zero_overround(self):
        """Cuotas perfectamente justas deben tener overround ~0."""
        # 1/3 + 1/3 + 1/3 = 1.0 (sin margen)
        fair_odds = {"1": 3.0, "X": 3.0, "2": 3.0}
        result = calculate_odds_factor(fair_odds)
        assert abs(result["overround"]) < 0.01

    def test_invalid_odds_returns_invalid(self):
        """Cuotas menores o iguales a 1 deben considerarse inválidas."""
        invalid_odds = {"1": 0.5, "X": 4.20, "2": 6.50}  # 0.5 es inválido
        result = calculate_odds_factor(invalid_odds)
        assert result["valid"] is False

    def test_empty_odds_returns_invalid(self):
        result = calculate_odds_factor({})
        assert result["valid"] is False

    def test_blend_with_model_moves_toward_market(self):
        """Mezclar debe mover las probabilidades hacia el mercado."""
        # Modelo dice 50/30/20, mercado dice 65/20/15
        model = {"1": 50.0, "X": 30.0, "2": 20.0}
        odds = {"1": 1.54, "X": 4.50, "2": 7.00}  # Cuotas que dan ~65% al local

        blended = blend_with_model(model, odds, odds_weight=0.25)

        # La prob del local debe estar entre el modelo y el mercado
        assert blended["1"] > model["1"], "El mercado favorece al local, debe subir"

    def test_blend_sums_to_100(self):
        """La mezcla final debe sumar 100%."""
        model = {"1": 50.0, "X": 30.0, "2": 20.0}
        blended = blend_with_model(model, self.VALID_ODDS, odds_weight=0.25)
        total = sum(blended.values())
        assert abs(total - 100.0) < 0.5, f"La mezcla debe sumar 100, suma {total}"

    def test_blend_with_invalid_odds_returns_model(self):
        """Si las cuotas son inválidas, debe devolver las probabilidades del modelo."""
        model = {"1": 50.0, "X": 30.0, "2": 20.0}
        blended = blend_with_model(model, {}, odds_weight=0.25)
        assert blended == model
