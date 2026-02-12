"""
Script para analizar la quiniela de la jornada.
"""
import sys
from pathlib import Path
import json

# Configurar sys.path para incluir la raíz del proyecto y src
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))
if str(project_root / 'src') not in sys.path:
    sys.path.append(str(project_root / 'src'))

from config.settings import PROCESSED_DATA_DIR, RAW_DATA_DIR
from utils.data_loader import load_json_data, save_json_data
from analysis.predictor import PredictionEngine
from analysis.quiniela import QuinielaAnalyzer
from models.match import Match, Team
from datetime import datetime

def main():
    """Función principal para el análisis de la quiniela."""
    print("Iniciando análisis de la quiniela...")

    # Cargar datos necesarios
    quiniela_matches = load_json_data(RAW_DATA_DIR / "quiniela_matches.json")
    if not quiniela_matches:
        print("Error: No se encontraron partidos de la quiniela. Ejecute 'python main.py collect' primero.")
        return

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
            continue # Ignorar partidos con datos incompletos

    # Inicializar el motor de predicción y el analizador de quiniela
    predictor = PredictionEngine(historical_matches=historical_matches, standings=standings)
    analyzer = QuinielaAnalyzer(predictor=predictor)

    # Cargar próximos partidos
    la_liga_next = load_json_data(RAW_DATA_DIR / "la_liga_next_matches.json") or []
    segunda_next = load_json_data(RAW_DATA_DIR / "segunda_next_matches.json") or []
    upcoming_matches = la_liga_next + segunda_next

    # Generar apuestas
    quiniela_ticket = analyzer.generate_quiniela_bets(quiniela_matches, upcoming_matches)

    # Guardar resultados
    output_path = PROCESSED_DATA_DIR / "quiniela_predictions.json"
    
    # Convertir a formato serializable
    output_data = []
    for bet in quiniela_ticket.bets:
        p = bet.prediction
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

    print(f"Análisis de la quiniela completado. Resultados guardados en {output_path}")

if __name__ == "__main__":
    main()
