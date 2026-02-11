"""Motor de predicciones de partidos."""
from typing import Dict, List
from dataclasses import dataclass
from src.models.match import Match, Prediction
from src.analysis.factors import home_away, form, h2h, rest, importance
from src.config.settings import FACTOR_WEIGHTS

@dataclass
class PredictionEngine:
    """Motor de predicciones."""
    
    historical_matches: List[Match]
    standings: Dict[str, Dict]
    
    def predict(self, match: Match) -> Prediction:
        """Genera predicción para un partido."""
        factors = self._calculate_all_factors(match)
        
        # Probabilidades base (equiprobables)
        probs = {"1": 33.33, "X": 33.33, "2": 33.33}
        
        # Ajustar por factores
        total_adjustment = sum(factors.values())
        probs["1"] += total_adjustment
        probs["2"] -= total_adjustment
        
        # Normalizar
        probs = self._normalize_probabilities(probs)
        
        # Determinar apuesta recomendada
        recommended = max(probs.items(), key=lambda x: x[1])
        
        return Prediction(
            match=match,
            prob_home=probs["1"],
            prob_draw=probs["X"],
            prob_away=probs["2"],
            recommended_bet=recommended[0],
            confidence=recommended[1],
            factors=factors
        )
    
    def _calculate_all_factors(self, match: Match) -> Dict[str, float]:
        """Calcula todos los factores para un partido."""
        home_factor = home_away.calculate_home_away_factor(
            match.home_team.name, 
            self.historical_matches, 
            is_home=True
        ).get("factor", 0)
        
        away_factor = home_away.calculate_home_away_factor(
            match.away_team.name,
            self.historical_matches,
            is_home=False
        ).get("factor", 0)

        form_factor = form.calculate_form_factor(
            match.home_team.name,
            match.away_team.name,
            self.historical_matches
        )

        h2h_factor = h2h.calculate_h2h_factor(
            match.home_team.name,
            match.away_team.name,
            self.historical_matches
        )

        rest_factor = rest.calculate_rest_days_factor(
            match,
            self.historical_matches
        )

        importance_factor = importance.calculate_importance_factor(
            match.home_team.name,
            match.away_team.name,
            self.standings
        )

        # Ponderar y sumar los factores
        total_factor = (
            home_factor * FACTOR_WEIGHTS.get('home_advantage', 1.0) +
            away_factor * FACTOR_WEIGHTS.get('away_performance', -1.0) + # Resta si el visitante es fuerte fuera
            form_factor * FACTOR_WEIGHTS.get('form', 1.0) +
            h2h_factor * FACTOR_WEIGHTS.get('h2h', 1.0) +
            rest_factor * FACTOR_WEIGHTS.get('rest_days', 1.0) +
            importance_factor * FACTOR_WEIGHTS.get('importance', 1.0)
        )

        return {
            "home_away": home_factor,
            "away_performance": away_factor,
            "form": form_factor,
            "h2h": h2h_factor,
            "rest_days": rest_factor,
            "importance": importance_factor,
            "total": total_factor
        }
    
    def _normalize_probabilities(self, probs: Dict[str, float]) -> Dict[str, float]:
        """Normaliza probabilidades para que sumen 100."""
        # Asegurar valores positivos
        probs = {k: max(v, 1.0) for k, v in probs.items()}
        total = sum(probs.values())
        return {k: round(v / total * 100, 2) for k, v in probs.items()}
