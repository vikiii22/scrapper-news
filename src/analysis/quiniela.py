"""
Este módulo contiene la lógica para generar predicciones de quiniela.
"""
from typing import List, Dict, Any, Optional
from src.models.quiniela import QuinielaTicket, QuinielaBet
from src.models.prediction import Prediction
from src.analysis.predictor import PredictionEngine
from src.utils.normalizers import normalize_team_name

class QuinielaAnalyzer:
    """
    Analiza los partidos de la quiniela y genera las apuestas.
    """

    def __init__(self, predictor: PredictionEngine):
        self.predictor = predictor

    def generate_quiniela_bets(
        self,
        quiniela_matches: List[Dict],
        upcoming_matches: List[Dict]
    ) -> QuinielaTicket:
        """
        Genera las apuestas para un boleto de quiniela.
        """
        bets = []
        for q_match in quiniela_matches:
            # Normalizar nombres de equipos de la quiniela
            q_home_norm = normalize_team_name(q_match['equipo_local'])
            q_away_norm = normalize_team_name(q_match['equipo_visitante'])

            # Encontrar el partido correspondiente en los próximos partidos
            target_match = None
            for u_match in upcoming_matches:
                u_home_norm = normalize_team_name(u_match['home_team_name'])
                u_away_norm = normalize_team_name(u_match['away_team_name'])
                if q_home_norm == u_home_norm and q_away_norm == u_away_norm:
                    target_match = u_match
                    break
            
            if target_match:
                # Crear un objeto Match para el predictor
                from src.models.match import Match, Team
                from datetime import datetime

                match_obj = Match(
                    id=target_match['id'],
                    home_team=Team(id=target_match['home_team_id'], name=target_match['home_team_name']),
                    away_team=Team(id=target_match['away_team_id'], name=target_match['away_team_name']),
                    date=datetime.fromisoformat(target_match['date']),
                    league=target_match.get('league', 'Unknown')
                )
                
                # Generar predicción para el partido
                prediction = self.predictor.predict(match_obj)
                
                # Crear la apuesta
                bet = QuinielaBet(
                    prediction=prediction,
                    bet=prediction.recommended_bet
                )
                bets.append(bet)
            else:
                # Si no se encuentra el partido, se puede añadir una apuesta por defecto o marcarlo
                # Aquí simplemente lo omitimos, pero podría ser manejado de otra forma.
                pass

        return QuinielaTicket(bets=bets, cost=0.0) # El coste se puede calcular después
