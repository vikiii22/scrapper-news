"""Motor de predicciones de partidos."""
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import math
from src.models.match import Match
from src.models.prediction import Prediction
from src.models.player import Player
from src.scrapers.weather_api import WeatherCondition
from src.analysis.factors import home_away, form, h2h, rest, importance, weather, players, standings
from src.config.settings import (
    FACTOR_WEIGHTS, 
    DRAW_PROB_LA_LIGA, 
    DRAW_PROB_HYPERMOTION, 
    HOME_ADVANTAGE_GOALS, 
    INJURY_PENALTY_AMOUNT, 
    NEUTRAL_GROUND_TERMS
)

@dataclass
class PredictionEngine:
    """Motor de predicciones."""
    
    historical_matches: List[Match]
    standings: Dict[str, Dict]
    
        
    def _calculate_lambda(
        self, 
        team_name: str, 
        is_home: bool, 
        neutral_ground: bool,
        missing_players: Optional[List[Player]] = None
    ) -> float:
        """Calcula lambda para la distribución de Poisson."""
        matches = [
            m for m in self.historical_matches 
            if (m.home_team.name == team_name or m.away_team.name == team_name)
            and m.status.value == "finished"
        ]
        matches.sort(key=lambda x: x.date, reverse=True)
        recent = matches[:5]
        
        if not recent:
            return 1.2  # Valor por defecto razonable
            
        goals = []
        for m in recent:
            if m.home_team.name == team_name:
                goals.append(m.home_score if m.home_score is not None else 0)
            else:
                goals.append(m.away_score if m.away_score is not None else 0)
                
        avg_goals = sum(goals) / len(goals)
        
        # Ajuste por localía
        if is_home and not neutral_ground:
            avg_goals += HOME_ADVANTAGE_GOALS
            
        # Penalización por lesiones (Rating > 7.5 -> -15%)
        penalty = players.calculate_injury_penalty_multiplier(missing_players or [])
        avg_goals *= penalty
        
        return max(0.1, avg_goals) # Evitar lambda 0
        
    def _poisson_probability(self, k: int, lamb: float) -> float:
        """Calcula probabilidad de k goles con media lambda."""
        return (lamb**k * math.exp(-lamb)) / math.factorial(k)
        
    def _calculate_poisson_match_probs(
        self, 
        lamb_home: float, 
        lamb_away: float,
        league_id: int # Para ajuste de empate base
    ) -> Tuple[float, float, float, str]:
        """Calcula probabilidades 1X2 ajustadas y marcador más probable."""
        max_goals = 7
        prob_matrix = [[0.0] * max_goals for _ in range(max_goals)]
        
        prob_home_win = 0.0
        prob_draw = 0.0
        prob_away_win = 0.0
        
        best_score = (0, 0)
        max_prob = 0.0
        
        for i in range(max_goals):
            p_h = self._poisson_probability(i, lamb_home)
            for j in range(max_goals):
                p_a = self._poisson_probability(j, lamb_away)
                prob = p_h * p_a
                prob_matrix[i][j] = prob
                
                if prob > max_prob:
                    max_prob = prob
                    best_score = (i, j)
                
                if i > j:
                    prob_home_win += prob
                elif i < j:
                    prob_away_win += prob
                else:
                    prob_draw += prob
                    
        # Ajuste de empate por liga
        base_draw_prob = DRAW_PROB_LA_LIGA
        if league_id == 54: # "Segunda División" ID from settings
             base_draw_prob = DRAW_PROB_HYPERMOTION
             
        # Normalizar primero
        total_prob = prob_home_win + prob_draw + prob_away_win
        if total_prob > 0:
            prob_home = prob_home_win / total_prob
            prob_draw = prob_draw / total_prob
            prob_away = prob_away_win / total_prob
        else:
            return 33.3, 33.3, 33.3, "0-0"

        # Aplicar corrección de empate base
        # Si la prob calculada es muy diferente de la base, la acercamos
        diff = base_draw_prob - prob_draw
        correction = diff * 0.5 # Corregimos el 50% de la diferencia
        
        prob_draw += correction
        prob_home -= correction / 2
        prob_away -= correction / 2
        
        # Re-normalizar y devolver porcentajes
        total = prob_home + prob_draw + prob_away
        return (
            (prob_home / total) * 100, 
            (prob_draw / total) * 100, 
            (prob_away / total) * 100,
            f"{best_score[0]}-{best_score[1]}"
        )

    def predict(
        self, 
        match: Match, 
        weather_data: Optional[WeatherCondition] = None,
        home_players: Optional[List[Player]] = None, # Missing players
        away_players: Optional[List[Player]] = None, # Missing players
        home_lineup: Optional[List[Player]] = None, # Full/Available squad
        away_lineup: Optional[List[Player]] = None, # Full/Available squad
        home_key_players: Optional[List[Player]] = None,
        away_key_players: Optional[List[Player]] = None
    ) -> Prediction:
        """Genera predicción para un partido."""
        
        # 1. Calcular Factores tradicionales (como justificación y ajuste fino)
        factors = self._calculate_all_factors(
            match, 
            weather_data, 
            home_players, 
            away_players,
            home_lineup,
            away_lineup,
            home_key_players,
            away_key_players
        )
        
        # 2. Configuración del partido
        neutral_ground = False
        if match.venue:
            venue_lower = match.venue.lower()
            if any(term in venue_lower for term in NEUTRAL_GROUND_TERMS):
                neutral_ground = True
            # Check específico de Butarque si es necesario, o genérico "neutral"
            if "butarque" in venue_lower and match.home_team.name.lower() != "leganes": # Ejemplo
                 pass # Por ahora confiamos en NEUTRAL_GROUND_TERMS
                 
        # 3. Calcular Lambdas (Goles esperados)
        lambda_home = self._calculate_lambda(
            match.home_team.name, 
            is_home=True, 
            neutral_ground=neutral_ground,
            missing_players=home_players
        )
        
        lambda_away = self._calculate_lambda(
            match.away_team.name, 
            is_home=False, 
            neutral_ground=neutral_ground, 
            missing_players=away_players
        )
        
        # 4. Calcular Probabilidades Poisson
        # Identificar Liga ID
        league_id = 8 # Default La Liga
        if match.league and "segunda" in match.league.lower():
            league_id = 54
            
        prob_home, prob_draw, prob_away, exact_score = self._calculate_poisson_match_probs(
            lambda_home, 
            lambda_away,
            league_id
        )
        
        probs = {"1": prob_home, "X": prob_draw, "2": prob_away}
        
        # 5. Ajuste final con factores (Opcional, pero recomendado para incluir clima/racha H2H que Poisson no ve directamente)
        # El Poisson se basa mucho en goles recientes.
        # Los factores ven H2H historico, clima, cansancio etc.
        # Vamos a usar los factores para 'impulsar' ligeramente la probabilidad
        
        total_adjustment = factors.get('total', 0)
        sensitivity = 0.5 # Menor peso porque Poisson ya es robusto
        
        probs["1"] += total_adjustment * sensitivity
        probs["2"] -= total_adjustment * sensitivity
        
        # Renormalizar
        total = sum(probs.values())
        if total > 0:
            probs = {k: (v / total) * 100 for k, v in probs.items()}
            
        # Determinar apuesta recomendada
        recommended = max(probs.items(), key=lambda x: x[1])
        
        # Añadir justificación técnica en los factores
        factors["poisson_lambda_home"] = lambda_home
        factors["poisson_lambda_away"] = lambda_away
        factors["predicted_score"] = exact_score
        factors["neutral_ground"] = neutral_ground
        
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
        home_missing: Optional[List[Player]] = None,
        away_missing: Optional[List[Player]] = None,
        home_lineup: Optional[List[Player]] = None,
        away_lineup: Optional[List[Player]] = None,
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

        standings_factor = standings.calculate_standings_factor(
            match.home_team.name,
            match.away_team.name,
            self.standings
        )

        weather_res = weather.calculate_weather_impact(match, weather_data)
        weather_factor = weather_res.get("weather_factor", 0.0)

        players_factor = 0.0
        
        # 1. Calculo de impacto de Bajas (Missing Players)
        if home_missing or away_missing:
            # En players.py: calculate_squad_impact
            # Usamos listas vacías si son None para evitar errores
            players_res = players.calculate_squad_impact(
                home_missing or [], 
                away_missing or [],
                home_key_players or [],
                away_key_players or []
            )
            players_factor += players_res.get("players_factor", 0.0)

        # 2. Calculo de fuerza relativa de plantilla (Squad Strength)
        if home_lineup and away_lineup:
            strength_res = players.calculate_squad_strength(home_lineup, away_lineup)
            # Sumamos al factor de jugadores existente
            # Si strength > 0 (Local mejor), aumenta players_factor
            players_factor += strength_res.get("strength_factor", 0.0)

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
            standings_factor * FACTOR_WEIGHTS.get('standings', 1.0) +
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
            "standings": standings_factor,
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
