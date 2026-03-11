"""Motor de predicciones de partidos."""
from typing import Dict, List, Optional, Tuple, Any
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
    NEUTRAL_GROUND_TERMS,
    XG_WEIGHT,
)
from src.utils.normalizers import normalize_team_name

@dataclass
class PredictionEngine:
    """Motor de predicciones."""
    
    historical_matches: List[Match]
    standings: List[Dict]
    
        
    def _calculate_lambda(
        self,
        team_name: str,
        opponent_name: str,
        is_home: bool,
        neutral_ground: bool,
        missing_players: Optional[List[Player]] = None,
        xg_data: Optional[Dict[str, float]] = None,
    ) -> float:
        """Calcula lambda para la distribución de Poisson.
        
        Integra xG (Expected Goals) si está disponible, ponderando:
            lambda = (1 - XG_WEIGHT) * avg_goals + XG_WEIGHT * avg_xg
        Esto suaviza las fluctuaciones de goles reales usando el rendimiento
        esperado basado en oportunidades creadas.
        """
        team_overall = self._get_recent_team_metrics(team_name)
        team_context = self._get_recent_team_metrics(
            team_name,
            venue_filter="home" if is_home else "away",
        )
        opponent_overall = self._get_recent_team_metrics(opponent_name)
        opponent_context = self._get_recent_team_metrics(
            opponent_name,
            venue_filter="away" if is_home else "home",
        )

        if team_overall["matches_analyzed"] == 0:
            return 1.2  # Valor por defecto razonable

        attack_strength = self._blend_metric(
            team_overall["goals_for"],
            team_context["goals_for"],
            team_context["matches_analyzed"],
        )
        opponent_defense = self._blend_metric(
            opponent_overall["goals_against"],
            opponent_context["goals_against"],
            opponent_context["matches_analyzed"],
        )
        avg_goals = attack_strength * 0.62 + opponent_defense * 0.38

        points_delta = team_overall["points_per_match"] - opponent_overall["points_per_match"]
        avg_goals *= 1 + self._clamp(points_delta * 0.12, -0.18, 0.18)

        if xg_data:
            xg_key = "home_xg" if is_home else "away_xg"
            avg_xg = xg_data.get(xg_key, 0.0)
            if avg_xg > 0:
                avg_goals = (1 - XG_WEIGHT) * avg_goals + XG_WEIGHT * avg_xg

        if is_home and not neutral_ground:
            avg_goals += HOME_ADVANTAGE_GOALS

        penalty = players.calculate_injury_penalty_multiplier(missing_players or [])
        avg_goals *= penalty

        return self._clamp(avg_goals, 0.15, 3.5)

    def _get_recent_team_metrics(
        self,
        team_name: str,
        venue_filter: Optional[str] = None,
        limit: int = 6,
    ) -> Dict[str, float]:
        """Extrae métricas recientes del equipo, separando local/visitante si se pide."""
        normalized_team = normalize_team_name(team_name)
        matches = []
        for match in self.historical_matches:
            if match.status.value != "finished":
                continue
            home_name = normalize_team_name(match.home_team.name)
            away_name = normalize_team_name(match.away_team.name)
            is_home = home_name == normalized_team
            is_away = away_name == normalized_team
            if not (is_home or is_away):
                continue
            if venue_filter == "home" and not is_home:
                continue
            if venue_filter == "away" and not is_away:
                continue
            matches.append(match)

        matches.sort(key=lambda current: current.date, reverse=True)
        recent = matches[:limit]
        if not recent:
            return {
                "goals_for": 1.2,
                "goals_against": 1.2,
                "points_per_match": 1.0,
                "matches_analyzed": 0,
            }

        weights = [0.30, 0.25, 0.18, 0.12, 0.09, 0.06][: len(recent)]
        weights_sum = sum(weights) or 1.0
        weights = [weight / weights_sum for weight in weights]

        goals_for = 0.0
        goals_against = 0.0
        points_total = 0.0
        for index, match in enumerate(recent):
            weight = weights[index]
            is_home = normalize_team_name(match.home_team.name) == normalized_team
            scored = match.home_score if is_home else match.away_score
            conceded = match.away_score if is_home else match.home_score
            goals_for += float(scored or 0) * weight
            goals_against += float(conceded or 0) * weight
            if (is_home and match.result == "1") or (not is_home and match.result == "2"):
                points_total += 3 * weight
            elif match.result == "X":
                points_total += 1 * weight

        return {
            "goals_for": goals_for,
            "goals_against": goals_against,
            "points_per_match": points_total,
            "matches_analyzed": len(recent),
        }

    def _blend_metric(self, overall_value: float, context_value: float, context_matches: int) -> float:
        """Combina rendimiento global y contextual sin sobreajustar a muestras pequeñas."""
        if context_matches <= 0:
            return overall_value
        context_weight = 0.45 if context_matches >= 3 else 0.25
        return overall_value * (1 - context_weight) + context_value * context_weight

    def _calculate_draw_adjustment(self, factors: Dict[str, float]) -> float:
        """Ajusta el empate según equilibrio real y tensión competitiva."""
        strength_gap = (
            abs(factors.get("standings", 0.0)) * 0.45 +
            abs(factors.get("form", 0.0)) * 0.30 +
            abs(factors.get("players", 0.0)) * 0.10 +
            abs(factors.get("h2h", 0.0)) * 0.10 +
            abs(factors.get("home_away", 0.0) - factors.get("away_performance", 0.0)) * 0.05
        )
        closeness = max(0.0, 1.0 - min(strength_gap / 4.5, 1.0))
        tension = min(factors.get("importance_tension", 0.0) / 4.0, 1.0)
        base_adjustment = (closeness - 0.5) * 8.0
        pressure_adjustment = tension * (1.2 if closeness >= 0.55 else -0.8)
        return round(self._clamp(base_adjustment + pressure_adjustment, -6.0, 6.0), 2)

    def _apply_draw_adjustment(self, probs: Dict[str, float], draw_adjustment: float) -> None:
        """Redistribuye probabilidad entre 1/X/2 en función del equilibrio del duelo."""
        if abs(draw_adjustment) < 0.01:
            return

        probs["X"] += draw_adjustment
        if draw_adjustment > 0:
            probs["1"] -= draw_adjustment / 2
            probs["2"] -= draw_adjustment / 2
        else:
            boost = abs(draw_adjustment)
            favorite = "1" if probs["1"] >= probs["2"] else "2"
            underdog = "2" if favorite == "1" else "1"
            probs[favorite] += boost * 0.7
            probs[underdog] += boost * 0.3

        for sign in ["1", "X", "2"]:
            probs[sign] = max(probs[sign], 1.0)

    def _clamp(self, value: float, minimum: float, maximum: float) -> float:
        """Limita un valor a un rango."""
        return max(min(value, maximum), minimum)
        
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
        home_players: Optional[List[Player]] = None,   # Missing players
        away_players: Optional[List[Player]] = None,   # Missing players
        home_lineup: Optional[List[Player]] = None,    # Full/Available squad
        away_lineup: Optional[List[Player]] = None,    # Full/Available squad
        home_key_players: Optional[List[Player]] = None,
        away_key_players: Optional[List[Player]] = None,
        match_statistics: Optional[Dict] = None,       # xG y SOG de SofaScore
        market_odds: Optional[Dict] = None,            # {"1": 1.45, "X": 4.20, "2": 6.50}
        losilla_percentages: Optional[Dict] = None,    # {"jugados": {...}, "lae": {...}, "probables": {...}}
        global_matches: Optional[List[Dict[str, Any]]] = None, # Partidos globales de MongoDB
    ) -> Prediction:
        """Genera predicción para un partido."""
        
        # 1. Calcular Factores tradicionales (como justificación y ajuste fino)
        factors = self._calculate_all_factors(
            match=match, 
            weather_data=weather_data, 
            home_missing=home_players, 
            away_missing=away_players,
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            home_key_players=home_key_players,
            away_key_players=away_key_players,
            global_matches=global_matches
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
                 
        # 3. Calcular Lambdas (Goles esperados) — con xG si disponible
        lambda_home = self._calculate_lambda(
            match.home_team.name,
            match.away_team.name,
            is_home=True,
            neutral_ground=neutral_ground,
            missing_players=home_players,
            xg_data=match_statistics,
        )

        lambda_away = self._calculate_lambda(
            match.away_team.name,
            match.home_team.name,
            is_home=False,
            neutral_ground=neutral_ground,
            missing_players=away_players,
            xg_data=match_statistics,
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
        
        # 5. Ajuste con factores clásicos (H2H, forma, clima, cansancio...)
        # Los factores ven información que Poisson no captura directamente.
        total_adjustment = factors.get('total', 0)
        sensitivity = 0.5  # Menor peso porque Poisson ya es robusto

        probs["1"] += total_adjustment * sensitivity
        probs["2"] -= total_adjustment * sensitivity

        draw_adjustment = self._calculate_draw_adjustment(factors)
        self._apply_draw_adjustment(probs, draw_adjustment)

        # 6. Integración de cuotas de mercado (prior bayesiano)
        # El mercado agrega información de cientos de analistas.
        # Mezclamos: prob_final = (1-w)*prob_modelo + w*prob_mercado
        odds_weight = FACTOR_WEIGHTS.get('odds', 0.0)
        if market_odds and odds_weight > 0:
            market_probs = self._convert_odds_to_probs(market_odds)
            if market_probs:
                for sign in ["1", "X", "2"]:
                    model_p = probs.get(sign, 33.3)
                    mkt_p = market_probs.get(sign, 33.3)
                    probs[sign] = (1 - odds_weight) * model_p + odds_weight * mkt_p

        # 7. Integración de porcentajes de Losilla (prior bayesiano)
        # Los %Probables de Losilla reflejan probabilidad estadística basada en datos reales de liga
        # Los %Jugados muestran la sabiduría de la multitud de quinielistas
        # Mezclamos: prob_final = (1-w)*prob_modelo + w*prob_losilla
        losilla_weight = FACTOR_WEIGHTS.get('losilla', 0.0)
        if losilla_percentages and losilla_weight > 0:
            # Priorizar %Probables (datos estadísticos), con fallback a %Jugados (sabiduría multitud)
            losilla_probs = None
            if 'probables' in losilla_percentages and losilla_percentages['probables']:
                losilla_probs = self._normalize_losilla_percentages(losilla_percentages['probables'])
            elif 'jugados' in losilla_percentages and losilla_percentages['jugados']:
                losilla_probs = self._normalize_losilla_percentages(losilla_percentages['jugados'])
            
            if losilla_probs:
                for sign in ["1", "X", "2"]:
                    model_p = probs.get(sign, 33.3)
                    losilla_p = losilla_probs.get(sign, 33.3)
                    probs[sign] = (1 - losilla_weight) * model_p + losilla_weight * losilla_p

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
        factors["xg_used"] = match_statistics is not None
        factors["odds_used"] = market_odds is not None
        factors["losilla_used"] = losilla_percentages is not None
        
        # Si se usó Losilla, incluir detalles en factores para transparencia
        if losilla_percentages:
            factors["losilla_data"] = {
                "jugados": losilla_percentages.get("jugados", {}),
                "probables": losilla_percentages.get("probables", {}),
                "lae": losilla_percentages.get("lae", {})
            }
        
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
        away_key_players: Optional[List[Player]] = None,
        global_matches: Optional[List[Dict[str, Any]]] = None
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
            self.historical_matches,
            self.standings,
        )

        h2h_factor = h2h.calculate_h2h_factor(
            match.home_team.name,
            match.away_team.name,
            self.historical_matches
        )

        rest_factor = rest.calculate_rest_days_factor(
            match,
            self.historical_matches,
            global_matches
        )

        importance_context = importance.calculate_match_context(
            match.home_team.name,
            match.away_team.name,
            self.standings
        )
        importance_factor = importance_context["swing"]

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
            "importance_tension": importance_context["tension"],
            "match_balance": importance_context["balance"],
            "standings": standings_factor,
            "weather": weather_factor,
            "players": players_factor,
            "total": total_factor
        }
    
    def _convert_odds_to_probs(self, odds: Dict[str, float]) -> Dict[str, float]:
        """Convierte cuotas decimales a probabilidades normalizadas (elimina overround).
        
        Ejemplo: {"1": 1.45, "X": 4.20, "2": 6.50}
        Probabilidades implícitas: 1/1.45=0.689, 1/4.20=0.238, 1/6.50=0.154
        Overround = 0.689 + 0.238 + 0.154 = 1.081 (8.1% margen casa)
        Normalizadas: 0.689/1.081=63.7%, 0.238/1.081=22.0%, 0.154/1.081=14.2%
        """
        try:
            raw = {}
            for sign in ["1", "X", "2"]:
                odd_val = float(odds.get(sign, 0))
                if odd_val > 1.0:
                    raw[sign] = 1.0 / odd_val
                else:
                    return {}  # Cuota inválida, no usar mercado
            
            total = sum(raw.values())
            if total <= 0:
                return {}
            
            return {
                "1": (raw["1"] / total) * 100,
                "X": (raw["X"] / total) * 100,
                "2": (raw["2"] / total) * 100,
            }
        except (TypeError, ValueError, ZeroDivisionError):
            return {}

    def _normalize_losilla_percentages(self, losilla_data: Dict[str, float]) -> Dict[str, float]:
        """Convierte porcentajes de Losilla a probabilidades normalizadas.
        
        Losilla devuelve datos en formato {"1": 36.1, "X": 26.3, "2": 37.6}
        Ya están normalizados (suman ~100), pero revalidamos por si acaso.
        """
        try:
            # Extraer los valores de 1, X, 2
            probs = {
                "1": float(losilla_data.get("1", 0)),
                "X": float(losilla_data.get("X", 0)),
                "2": float(losilla_data.get("2", 0))
            }
            
            total = sum(probs.values())
            if total <= 0:
                return {}
            
            # Normalizar para asegurar que suman exactamente 100
            return {
                "1": (probs["1"] / total) * 100,
                "X": (probs["X"] / total) * 100,
                "2": (probs["2"] / total) * 100,
            }
        except (TypeError, ValueError, KeyError):
            return {}

    def _normalize_probabilities(self, probs: Dict[str, float]) -> Dict[str, float]:
        """Normaliza probabilidades para que sumen 100."""
        # Asegurar valores positivos
        probs = {k: max(v, 1.0) for k, v in probs.items()}
        total = sum(probs.values())
        return {k: round(v / total * 100, 2) for k, v in probs.items()}
