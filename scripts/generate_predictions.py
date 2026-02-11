"""
Script para generar predicciones para los próximos partidos.
"""
import sys
from pathlib import Path
import json

# Añadir el directorio src al path
sys.path.append(str(Path(__file__).resolve().parent.parent / 'src'))

from config.settings import PROCESSED_DATA_DIR, RAW_DATA_DIR
from utils.data_loader import load_json_data, save_json_data
from analysis.predictor import PredictionEngine
from models.match import Match, Team
from datetime import datetime

def main():
    """Función principal para la generación de predicciones."""
    print("Iniciando generación de predicciones...")

    # Cargar datos necesarios
    la_liga_standings = load_json_data(RAW_DATA_DIR / "la_liga_standings.json")
    segunda_standings = load_json_data(RAW_DATA_DIR / "segunda_standings.json")
    standings = la_liga_standings + segunda_standings if la_liga_standings and segunda_standings else []

    la_liga_matches = load_json_data(RAW_DATA_DIR / "la_liga_all_matches.json") or []
    segunda_matches = load_json_data(RAW_DATA_DIR / "segunda_all_matches.json") or []
    historical_matches_raw = la_liga_matches + segunda_matches

    # Convertir datos raw a objetos Match
    historical_matches = []
    for m in historical_matches_raw:
        try:
            historical_matches.append(
                Match(
                    id=m['id'],
                    home_team=Team(id=m['home_team_id'], name=m['home_team_name']),
                    away_team=Team(id=m['away_team_id'], name=m['away_team_name']),
                    date=datetime.fromisoformat(m['date']),
                    league=m.get('league', 'Unknown'),
                    home_score=m.get('home_score'),
                    away_score=m.get('away_score')
                )
            )
        except (KeyError, TypeError):
            continue

    # Inicializar el motor de predicción
    predictor = PredictionEngine(historical_matches=historical_matches, standings=standings)

    # Cargar próximos partidos
    la_liga_next = load_json_data(RAW_DATA_DIR / "la_liga_next_matches.json") or []
    segunda_next = load_json_data(RAW_DATA_DIR / "segunda_next_matches.json") or []
    upcoming_matches_raw = la_liga_next + segunda_next

    predictions = []
    for m in upcoming_matches_raw:
        try:
            match_obj = Match(
                id=m['id'],
                home_team=Team(id=m['home_team_id'], name=m['home_team_name']),
                away_team=Team(id=m['away_team_id'], name=m['away_team_name']),
                date=datetime.fromisoformat(m['date']),
                league=m.get('league', 'Unknown')
            )
            prediction = predictor.predict(match_obj)
            predictions.append(prediction)
        except (KeyError, TypeError):
            continue

    # Guardar resultados
    output_path = PROCESSED_DATA_DIR / "upcoming_match_predictions.json"
    
    # Convertir a formato serializable
    output_data = []
    for p in predictions:
        output_data.append({
            "match_info": {
                "home_team": p.match.home_team.name,
                "away_team": p.match.away_team.name,
                "date": p.match.date.isoformat(),
            },
            "prediction": p.recommended_bet,
            "confidence": p.confidence,
            "probabilities": {
                "home": p.prob_home,
                "draw": p.prob_draw,
                "away": p.prob_away,
            }
        })

    save_json_data(output_data, output_path)

    print(f"Generación de predicciones completada. Resultados guardados en {output_path}")

if __name__ == "__main__":
    main()
