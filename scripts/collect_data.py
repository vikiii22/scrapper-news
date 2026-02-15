"""
Script para recolectar datos de todas las fuentes.
"""
import sys
from pathlib import Path
import json

# Añadir el directorio src al path
sys.path.append(str(Path(__file__).resolve().parent.parent / 'src'))

from config.settings import LEAGUES, RAW_DATA_DIR
from scrapers.sofascore import SofascoreScraper
from scrapers.news_scraper import NewsScraper
from scrapers.quiniela_html import QuinielaHtmlParser
from utils.data_loader import save_json_data
import time

def main():
    """Función principal para la recolección de datos."""
    print("Iniciando recolección de datos...")
    
    # --- News Scraper ---
    # Recolectar noticias primero para tener contexto logístico
    print("Recolectando noticias deportivas (Marca, AS)...")
    try:
        news_scraper = NewsScraper()
        news_data = news_scraper.run() # No specific players yet, just logistic check
        save_json_data(news_data, RAW_DATA_DIR / "news_data.json")
        print(f"  Noticias guardadas en {RAW_DATA_DIR / 'news_data.json'}")
    except Exception as e:
        print(f"  Error recolectando noticias: {e}")

    # --- Sofascore ---
    sofascore_scraper = SofascoreScraper()
    for league_name, league_config in LEAGUES.items():
        print(f"Recolectando datos de Sofascore para {league_config.name}...")
        
        # Obtener clasificación
        standings = sofascore_scraper.get_standings(league_config.id, league_config.season_id)
        save_json_data(standings, RAW_DATA_DIR / f"{league_name}_standings.json")
        print(f"  Clasificación guardada.")

        # Obtener todos los partidos (Histórico)
        all_matches = sofascore_scraper.get_all_matches(league_config.id, league_config.season_id)
        
        # ENRIQUECIMIENTO DE DATOS HISTÓRICOS (Últimos 20 partidos para análisis de forma/xG)
        print("    Enriqueciendo últimos 20 partidos finalizados con xG y SOG...")
        # Tomamos los ultimos 20 (asumiendo que están ordenados por fecha)
        recent_matches = all_matches[-20:] if len(all_matches) > 20 else all_matches
        
        for match in recent_matches:
            try:
                match_id = match.get('id')
                print(f"      Procesando ID {match_id}...", end="\r")
                
                # Estadísticas avanzadas (xG, SOG)
                stats = sofascore_scraper.get_match_statistics(match_id)
                match['statistics'] = stats
                
                # Ratings de jugadores (Lineups pasados)
                lineups = sofascore_scraper.get_match_lineups(match_id)
                match['lineups'] = lineups
                
                time.sleep(1) # Respetar rate limits
            except Exception as e:
                print(f"      Error en partido {match_id}: {e}")
                
        # Guardar todo (con los enriquecidos actualizados en la lista original por referencia)
        save_json_data(all_matches, RAW_DATA_DIR / f"{league_name}_all_matches.json")
        print(f"  Partidos jugados (con detalles recientes) guardados.")

        # Obtener próximos partidos
        next_matches = sofascore_scraper.get_next_matches(league_config.id, league_config.season_id)
        
        # ENRIQUECIMIENTO DE PRÓXIMOS PARTIDOS
        print("    Verificando alineaciones confirmadas para próximos partidos...")
        for match in next_matches:
             try:
                match_id = match.get('id')
                lineups = sofascore_scraper.get_match_lineups(match_id)
                match['lineups'] = lineups
                time.sleep(0.5)
             except Exception as e:
                 pass
                 
        save_json_data(next_matches, RAW_DATA_DIR / f"{league_name}_next_matches.json")
        print(f"  Próximos partidos guardados.")


    # --- Quiniela HTML ---
    quiniela_html_path = Path(__file__).resolve().parent.parent / 'data' / 'Jornada_quiniela.html'
    if quiniela_html_path.exists():
        print("Recolectando datos de la Quiniela...")
        quiniela_parser = QuinielaHtmlParser(quiniela_html_path)
        quiniela_matches = quiniela_parser.run()
        save_json_data(quiniela_matches, RAW_DATA_DIR / "quiniela_matches.json")
        print(f"  Partidos de la quiniela guardados en {RAW_DATA_DIR / 'quiniela_matches.json'}")
    else:
        print(f"ADVERTENCIA: No se encontró el archivo {quiniela_html_path}. No se procesará la quiniela.")

    print("Recolección de datos finalizada.")

if __name__ == "__main__":
    main()
