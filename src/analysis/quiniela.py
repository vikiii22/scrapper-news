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

    def __init__(
        self, 
        predictor: PredictionEngine, 
        global_matches: Optional[List[Dict[str, Any]]] = None,
        losilla_data: Optional[Dict[int, Dict[str, Dict[str, float]]]] = None
    ):
        self.predictor = predictor
        self.global_matches = global_matches
        self.losilla_data = losilla_data or {}

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
            
            # Obtener el número de partido de la quiniela (1-15)
            # Convertir a int porque losilla_data usa keys enteros
            match_number = q_match.get('numero', None)
            if match_number is not None:
                try:
                    match_number = int(match_number)
                except (ValueError, TypeError):
                    match_number = None

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
                
                # Obtener porcentajes de Losilla para este partido si están disponibles
                losilla_percentages = None
                if match_number is not None and match_number in self.losilla_data:
                    losilla_percentages = self.losilla_data[match_number]
                
                # Generar predicción para el partido
                prediction = self.predictor.predict(
                    match_obj,
                    global_matches=self.global_matches,
                    losilla_percentages=losilla_percentages
                )
                
                # Crear la apuesta
                bet = QuinielaBet(
                    prediction=prediction,
                    bet=prediction.recommended_bet
                )
                bets.append(bet)
            else:
                print(f"WARNING: No data found for match: {q_match['equipo_local']} vs {q_match['equipo_visitante']}")
                print(f"   (Normalized Quiniela: {q_home_norm} vs {q_away_norm})")

        return QuinielaTicket(bets=bets, cost=0.0) # El coste se puede calcular después
