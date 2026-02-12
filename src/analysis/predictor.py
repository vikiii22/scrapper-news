"""Motor de predicciones de partidos."""
from typing import Dict, List, Optional
from dataclasses import dataclass
from src.models.match import Match
from src.models.prediction import Prediction
from src.models.player import Player
from src.scrapers.weather_api import WeatherCondition
from src.analysis.factors import home_away, form, h2h, rest, importance, weather, players
from src.config.settings import FACTOR_WEIGHTS

@dataclass
class PredictionEngine:
    """Motor de predicciones."""
    
    historical_matches: List[Match]
    standings: Dict[str, Dict]
    
    def predict(
        self, 
        match: Match, 
        weather_data: Optional[WeatherCondition] = None,
        home_players: Optional[List[Player]] = None,
        away_players: Optional[List[Player]] = None,
        home_key_players: Optional[List[Player]] = None,
        away_key_players: Optional[List[Player]] = None
    ) -> Prediction:
        """Genera predicción para un partido."""
        factors = self._calculate_all_factors(
            match, 
            weather_data, 
            home_players, 
            away_players,
            home_key_players,
            away_key_players
        )
        
        # Probabilidades base (equiprobables)
        probs = {"1": 33.33, "X": 33.33, "2": 33.33}
        
        # Ajustar por factores
        # Usamos SOLO 'total' que ya contiene la suma ponderada
        total_adjustment = factors.get('total', 0)
        
        # Aplicamos el ajuste:
        # Si total_adjustment es positivo => favorece al Local ("1")
        # Si total_adjustment es negativo => favorece al Visitante ("2")
        
        # Factor de sensibilidad para convertir puntos de factor a % de probabilidad
        # Reducido de 2.5 a 1.2 para evitar predicciones extremas (ej. 80% vs 1%)
        sensitivity = 1.2
        
        probs["1"] += total_adjustment * sensitivity
        probs["2"] -= total_adjustment * sensitivity
        
        # El empate también se ve afectado ligeramente si hay mucha disparidad
        # Si hay un claro favorito, la probabilidad de empate baja un poco
        probs["X"] -= abs(total_adjustment * (sensitivity * 0.3)) 
        
        # Normalizar para asegurar que suman 100% y no hay negativos
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
    
    def _calculate_all_factors(
        self, 
        match: Match,
        weather_data: Optional[WeatherCondition] = None,
        home_players: Optional[List[Player]] = None,
        away_players: Optional[List[Player]] = None,
        home_key_players: Optional[List[Player]] = None,
        away_key_players: Optional[List[Player]] = None
    ) -> Dict[str, float]:
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

        weather_res = weather.calculate_weather_impact(match, weather_data)
        weather_factor = weather_res.get("weather_factor", 0.0)

        players_factor = 0.0
        if home_players and away_players:
            # Asumimos que home_players son los bajas/missing por ahora o 
            # necesitamos ajustar la logica de llamada.
            # En players.py: calculate_squad_impact(home_missing, away_missing, home_key, away_key)
            players_res = players.calculate_squad_impact(
                home_players or [], 
                away_players or [],
                home_key_players or [],
                away_key_players or []
            )
            players_factor = players_res.get("players_factor", 0.0)

        # Ponderar y sumar los factores
        # IMPORTANTE: away_factor suele ser positivo si rinden bien fuera,
        # pero aquí queremos sumar al local ("1").
        # Si local es fuerte => home_factor > 0 => suma a "1"
        # Si visitante es fuerte => away_factor > 0 => RESTA a "1" (suma a "2")
        
        total_factor = (
            home_factor * FACTOR_WEIGHTS.get('home_advantage', 1.0) -
            away_factor * abs(FACTOR_WEIGHTS.get('away_performance', 1.0)) + 
            form_factor * FACTOR_WEIGHTS.get('form', 1.0) +
            h2h_factor * FACTOR_WEIGHTS.get('h2h', 1.0) +
            rest_factor * FACTOR_WEIGHTS.get('rest_days', 1.0) +
            importance_factor * FACTOR_WEIGHTS.get('importance', 1.0) +
            weather_factor * FACTOR_WEIGHTS.get('weather', 1.0) +
            players_factor * FACTOR_WEIGHTS.get('players', 1.0)
        )

        return {
            "home_away": home_factor,
            "away_performance": away_factor,
            "form": form_factor,
            "h2h": h2h_factor,
            "rest_days": rest_factor,
            "importance": importance_factor,
            "weather": weather_factor,
            "players": players_factor,
            "total": total_factor
        }
    
    def _normalize_probabilities(self, probs: Dict[str, float]) -> Dict[str, float]:
        """Normaliza probabilidades para que sumen 100."""
        # Asegurar valores positivos
        probs = {k: max(v, 1.0) for k, v in probs.items()}
        total = sum(probs.values())
        return {k: round(v / total * 100, 2) for k, v in probs.items()}
