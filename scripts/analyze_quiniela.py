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

from utils.mongo_loader import load_mongo_data, save_mongo_data
from config.settings import PROCESSED_DATA_DIR, RAW_DATA_DIR
from analysis.predictor import PredictionEngine
from analysis.quiniela import QuinielaAnalyzer
from models.match import Match, Team
from scrapers.losilla_scraper import LosillaScraper
from datetime import datetime

def main():
    """Función principal para el análisis de la quiniela."""
    print("Iniciando análisis de la quiniela...")

    # Cargar datos necesarios
    quiniela_matches = load_mongo_data("quiniela_matches")
    if not quiniela_matches:
        print("Error: No se encontraron partidos de la quiniela. Ejecute 'python main.py collect' primero.")
        return

    la_liga_standings = load_mongo_data("la_liga_standings")
    segunda_standings = load_mongo_data("segunda_standings")
    standings = la_liga_standings + segunda_standings if la_liga_standings and segunda_standings else []

    la_liga_matches = load_mongo_data("la_liga_all_matches")
    segunda_matches = load_mongo_data("segunda_all_matches")
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

    # Cargar partidos globales de MongoDB
    global_matches = load_mongo_data("global_recent_matches")

    # Obtener porcentajes de Losilla para la quiniela
    losilla_data = {}
    try:
        losilla_scraper = LosillaScraper()
        # Intentar determinar jornada y temporada de los datos de quiniela
        # Si no está disponible, usar valores actuales
        jornada = quiniela_matches[0].get('jornada', 46) if quiniela_matches else 46
        temporada = quiniela_matches[0].get('temporada', 2026) if quiniela_matches else 2026
        
        print(f"Obteniendo porcentajes de Losilla para jornada {jornada}, temporada {temporada}...")
        losilla_data = losilla_scraper.get_all_percentages(jornada=jornada, temporada=temporada)
        print(f"Porcentajes de Losilla obtenidos para {len(losilla_data)} partidos")
    except Exception as e:
        print(f"Advertencia: No se pudieron obtener porcentajes de Losilla: {e}")
        print("Continuando sin datos de Losilla...")

    # Inicializar el motor de predicción y el analizador de quiniela
    predictor = PredictionEngine(historical_matches=historical_matches, standings=standings)
    analyzer = QuinielaAnalyzer(
        predictor=predictor, 
        global_matches=global_matches,
        losilla_data=losilla_data
    )

    # Cargar próximos partidos
    la_liga_next = load_mongo_data("la_liga_next_matches")
    segunda_next = load_mongo_data("segunda_next_matches")
    upcoming_matches = la_liga_next + segunda_next

    # Generar apuestas
    quiniela_ticket = analyzer.generate_quiniela_bets(quiniela_matches, upcoming_matches)

    # Guardar resultados
    output_path = PROCESSED_DATA_DIR / "quiniela_predictions.json"
    
    # Convertir a formato serializable
    output_data = []
    for bet in quiniela_ticket.bets:
        p = bet.prediction
        match_data = {
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
        }
        
        # Incluir datos de Losilla si están disponibles en los factores
        if p.factors and "losilla_data" in p.factors:
            match_data["losilla_data"] = p.factors["losilla_data"]
        
        output_data.append(match_data)

    # Exportar en archivo estático para GitHub Pages ANTES de save_mongo_data
    # (pymongo muta los dicts añadiendo _id:ObjectId al hacer insert_many)
    app_api_dir = project_root / "app" / "api"
    app_api_dir.mkdir(parents=True, exist_ok=True)
    with open(app_api_dir / "predictions.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)

    save_mongo_data("quiniela_predictions", output_data)

    print(f"Análisis de la quiniela completado. Resultados guardados en MongoDB y en {app_api_dir / 'predictions.json'}")

if __name__ == "__main__":
    main()
