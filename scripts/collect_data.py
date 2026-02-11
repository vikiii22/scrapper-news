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
from scrapers.quiniela_html import QuinielaHtmlParser
from utils.data_loader import save_json_data

def main():
    """Función principal para la recolección de datos."""
    print("Iniciando recolección de datos...")

    # --- Sofascore ---
    sofascore_scraper = SofascoreScraper()
    for league_name, league_config in LEAGUES.items():
        print(f"Recolectando datos de Sofascore para {league_config.name}...")
        
        # Obtener clasificación
        standings = sofascore_scraper.get_standings(league_config.id, league_config.season_id)
        save_json_data(standings, RAW_DATA_DIR / f"{league_name}_standings.json")
        print(f"  Clasificación guardada en {RAW_DATA_DIR / f'{league_name}_standings.json'}")

        # Obtener todos los partidos
        all_matches = sofascore_scraper.get_all_matches(league_config.id, league_config.season_id)
        save_json_data(all_matches, RAW_DATA_DIR / f"{league_name}_all_matches.json")
        print(f"  Partidos jugados guardados en {RAW_DATA_DIR / f'{league_name}_all_matches.json'}")

        # Obtener próximos partidos
        next_matches = sofascore_scraper.get_next_matches(league_config.id, league_config.season_id)
        save_json_data(next_matches, RAW_DATA_DIR / f"{league_name}_next_matches.json")
        print(f"  Próximos partidos guardados en {RAW_DATA_DIR / f'{league_name}_next_matches.json'}")

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
