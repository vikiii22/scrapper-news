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
from utils.mongo_loader import save_mongo_data
from utils.data_loader import save_json_data  # Keeping import if accidentally needed elsewhere
from utils.mongo_loader import save_mongo_data
import time

def main():
    """Función principal para la recolección de datos."""
    print("Iniciando recolección de datos...")
    
    # --- Sofascore ---
    sofascore_scraper = SofascoreScraper()
    all_player_names = set() # To collect all unique player names

    for league_name, league_config in LEAGUES.items():
        print(f"Recolectando datos de Sofascore para {league_config.name}...")
        
        # Obtener clasificación
        standings = sofascore_scraper.get_standings(league_config.id, league_config.season_id)
        if standings:
            print(f"  Clasificación de {league_name} obtenida.")
            save_mongo_data(f"{league_name}_standings", standings)

        # Obtener todos los partidos (Histórico)
        all_matches = sofascore_scraper.get_all_matches(league_config.id, league_config.season_id)
        
        # ENRIQUECIMIENTO DE DATOS HISTÓRICOS (Últimos 20 partidos para análisis de forma/xG)
        print("    Enriqueciendo últimos 20 partidos finalizados con xG y SOG...")
        
        # We need all matches to extract player names for news scraper later
        # So we process all_matches and then take recent ones for enrichment if needed.
        # This assumes all_matches might contain player info for historical matches.
        
        # Extract player names from historical matches
        for match in all_matches:
            if match.get('lineups'):
                for side in ['home', 'away']:
                    if side in match['lineups'] and 'players' in match['lineups'][side]:
                        for player_item in match['lineups'][side]['players']:
                            if 'player' in player_item and 'name' in player_item['player']:
                                all_player_names.add(player_item['player']['name'])
                    if side in match['lineups'] and 'missingPlayers' in match['lineups'][side]:
                         for player_item in match['lineups'][side]['missingPlayers']:
                            if 'player' in player_item and 'name' in player_item['player']:
                                all_player_names.add(player_item['player']['name'])

        recent_matches_for_enrichment = all_matches[-20:] if len(all_matches) > 20 else all_matches
        
        for match in recent_matches_for_enrichment:
            try:
                match_id = match.get('id')
                print(f"      Procesando ID {match_id}...", end="\r")
                
                # Estadísticas avanzadas (xG, SOG)
                stats = sofascore_scraper.get_match_statistics(match_id)
                match['statistics'] = stats
                
                # Ratings de jugadores (Lineups pasados) - Already collected for all matches above if available
                # If not collected yet, we would collect here. But for now, we assume it's in all_matches
                # lineups = sofascore_scraper.get_match_lineups(match_id)
                # match['lineups'] = lineups
                
                time.sleep(1) # Respetar rate limits
            except Exception as e:
                print(f"      Error en partido {match_id}: {e}")
                
        # Guardar todo (con los enriquecidos actualizados en la lista original por referencia)
        if all_matches:
            print(f"  {len(all_matches)} partidos históricos obtenidos.")
            save_mongo_data(f"{league_name}_all_matches", all_matches)

        # Obtener próximos partidos
        next_matches = sofascore_scraper.get_next_matches(league_config.id, league_config.season_id)
        
        # ENRIQUECIMIENTO DE PRÓXIMOS PARTIDOS
        print("    Verificando alineaciones confirmadas para próximos partidos...")
        for match in next_matches:
             try:
                match_id = match.get('id')
                lineups = sofascore_scraper.get_match_lineups(match_id)
                match['lineups'] = lineups
                
                # Also collect player names from next matches
                if lineups:
                    for side in ['home', 'away']:
                        if side in lineups and 'players' in lineups[side]:
                            for player_item in lineups[side]['players']:
                                if 'player' in player_item and 'name' in player_item['player']:
                                    all_player_names.add(player_item['player']['name'])
                        if side in lineups and 'missingPlayers' in lineups[side]:
                            for player_item in lineups[side]['missingPlayers']:
                                if 'player' in player_item and 'name' in player_item['player']:
                                    all_player_names.add(player_item['player']['name'])
                
                time.sleep(0.5)
             except Exception as e:
                 pass
        if next_matches:
            print(f"  {len(next_matches)} próximos partidos obtenidos.")
            save_mongo_data(f"{league_name}_next_matches", next_matches)
    
    # --- News Scraper (now with player names) ---
    print("\nRecolectando noticias deportivas (Marca, AS) con detección de jugadores...")
    try:
        news_scraper = NewsScraper()
        player_names_list = list(all_player_names)
        print(f"  Pasando {len(player_names_list)} nombres de jugadores al scraper de noticias.")
        news_data = news_scraper.run(player_names=player_names_list)
        if news_data:
            print("  Noticias almacenadas.")
            save_mongo_data("news_data", news_data)
    except Exception as e:
        print(f"  Error recolectando noticias: {e}")

    # --- Quiniela HTML ---
    quiniela_html_path = Path(__file__).resolve().parent.parent / 'data' / 'Jornada_quiniela.html'
    quiniela_matches = []
    if quiniela_html_path.exists():
        print("Recolectando datos de la Quiniela...")
        quiniela_parser = QuinielaHtmlParser(quiniela_html_path)
        quiniela_matches = quiniela_parser.run()
        if quiniela_matches:
            print(f"  Partidos de la quiniela guardados en MongoDB.")
            save_mongo_data("quiniela_matches", quiniela_matches)
    else:
        print(f"ADVERTENCIA: No se encontró el archivo {quiniela_html_path}. No se procesará la quiniela.")

    # --- DATOS GLOBALES PARA FATIGA E INFO (equipos de La Liga y Quiniela) ---
    print("\nObteniendo datos globales (todas las competiciones) para los equipos...")
    
    # Recopilamos todos los team_id que hemos visto hoy para no repetir
    team_ids_to_fetch = set()
    
    # Load standings to find team ids easily
    from utils.mongo_loader import load_mongo_data
    
    for league_name in LEAGUES.keys():
        st = load_mongo_data(f"{league_name}_standings")
        if st:
            for row in st:
                if row.get('team_id'):
                    team_ids_to_fetch.add(row['team_id'])

    global_matches = []
    about_teams = []

    for idx, team_id in enumerate(team_ids_to_fetch):
        print(f"  [{idx+1}/{len(team_ids_to_fetch)}] Procesando equipo ID {team_id}...")
        try:
            # Info del equipo (About)
            print("    Obteniendo Información del equipo...")
            team_info = sofascore_scraper.get_team_info(team_id)
            if team_info:
                about_teams.append(team_info)
                
            # Partidos globales (all competitions)
            print("    Obteniendo Partidos Globales...")
            recent_matches = sofascore_scraper.get_team_recent_matches(team_id)
            
            # Asociamos a quíen pertenecen estos partidos para no mezclarnos
            for match in recent_matches:
                match['context_team_id'] = team_id
                global_matches.append(match)
            
            time.sleep(1) # Rate limit
        except Exception as e:
            print(f"    Error procesando equipo {team_id}: {e}")

    if global_matches:
        print(f"  Guardando {len(global_matches)} partidos globales en MongoDB...")
        save_mongo_data("global_recent_matches", global_matches)
        
    if about_teams:
        print(f"  Guardando información de {len(about_teams)} equipos en MongoDB...")
        save_mongo_data("about_teams", about_teams)

    print("\nRecolección de datos finalizada.")

if __name__ == "__main__":
    main()

