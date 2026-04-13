"""
Script para generar predicciones para los próximos partidos.
"""
import sys
from pathlib import Path
import json

# Añadir el directorio src al path
sys.path.append(str(Path(__file__).resolve().parent.parent / 'src'))

from config.settings import PROCESSED_DATA_DIR, RAW_DATA_DIR, NEUTRAL_GROUND_TERMS
from utils.mongo_loader import load_mongo_data, save_mongo_data
from utils.normalizers import remove_accents
from analysis.predictor import PredictionEngine
from models.match import Match, Team
from models.player import Player
from scrapers.weather_api import WeatherClient
from scrapers.sofascore import SofascoreScraper
from scrapers.losilla_scraper import LosillaScraper
from datetime import datetime

def parse_players(lineups_data: dict, side: str, key: str = 'missingPlayers') -> list[Player]:
    """Extrae lista de jugadores (missing o lineup) del JSON de alineaciones."""
    players_list = []
    if not lineups_data or side not in lineups_data:
        return []
    
    # Sofascore structure: lineups -> home -> missingPlayers/players -> [{player: {...}}, ...]
    team_data = lineups_data.get(side, {})
    raw_list = team_data.get(key, [])
    
    for item in raw_list:
        p_data = item.get('player', {})
        if not p_data:
            continue
            
        try:
            # Intentar sacar rating si existe (a veces está en 'avgRating' o 'statistics')
            # En lineups confirmados a veces no hay rating (es pre-partido).
            # Si no hay rating, intentamos inferirlo o ponemos uno base.
            # Para 'strength' analysis, necesitamos alguna métrica de calidad.
            # Sofascore a veces da 'avgRating' en la temporada para el jugador.
            
            # Mockup rating logic for demo if not present
            rating = p_data.get('avgRating', 7.0) 
            
            # Si es missing, asumimos un rating alto por defecto para que duela la baja
            if key == 'missingPlayers':
                 rating = 7.5
            
            player = Player(
                id=p_data.get('id', 0),
                name=p_data.get('name', 'Unknown'),
                position=p_data.get('position', 'M'),
                team_id=0,
                rating=float(rating) if rating else 6.5,
                is_injured=(key == 'missingPlayers')
            )
            players_list.append(player)
        except Exception:
            continue
            
    return players_list

def _get_top_n_players_by_rating(players: List[Player], n: int = 3) -> List[Player]:
    """Extrae los N jugadores con mayor rating de una lista."""
    return sorted([p for p in players if p.rating is not None and p.rating > 0], 
                  key=lambda p: p.rating, reverse=True)[:n]

def main():
    """Función principal para la generación de predicciones."""
    print("Iniciando generación de predicciones...")

    weather_client = WeatherClient()
    scraper = SofascoreScraper()

    # Cargar datos necesarios
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
            continue

    # Cargar noticias
    news_data_list = load_mongo_data("news_data")
    news_data = news_data_list[0] if news_data_list else {}
    logistic_issues = news_data.get('logistic_issues', [])
    player_issues = news_data.get('player_issues', [])

    # Inicializar el motor de predicción
    predictor = PredictionEngine(historical_matches=historical_matches, standings=standings)
    
    # Cargar global_matches para usarlos
    global_matches = load_mongo_data("global_recent_matches")
    
    # Obtener porcentajes de Losilla para la quiniela
    losilla_data = {}
    quiniela = load_mongo_data("quiniela_matches")
    if quiniela:
        try:
            losilla_scraper = LosillaScraper()
            # Intentar determinar jornada y temporada de los datos de quiniela
            jornada = quiniela[0].get('jornada', 46) if quiniela else 46
            temporada = quiniela[0].get('temporada', 2026) if quiniela else 2026
            
            print(f"Obteniendo porcentajes de Losilla para jornada {jornada}, temporada {temporada}...")
            losilla_data = losilla_scraper.get_all_percentages(jornada=jornada, temporada=temporada)
            print(f"Porcentajes de Losilla obtenidos para {len(losilla_data)} partidos")
        except Exception as e:
            print(f"Advertencia: No se pudieron obtener porcentajes de Losilla: {e}")
            print("Continuando sin datos de Losilla...")

    # Cargar próximos partidos
    la_liga_next = load_mongo_data("la_liga_next_matches")
    segunda_next = load_mongo_data("segunda_next_matches")
    upcoming_matches_raw = la_liga_next + segunda_next

    # Cargar partidos de la Quiniela para filtrar
    quiniela_matches = load_mongo_data("quiniela_matches")
    
    # Crear set de pares para filtrado rápido (Normalizamos a minúsculas y sin acentos para comparar mejor)
    quiniela_pairs = [] # List of tuples to allow iterating
    if quiniela_matches:
        print(f"Filtrando por partidos de Quiniela ({len(quiniela_matches)} partidos)...")
        for q in quiniela_matches:
            # Usar los nombres normalizados si existen, o los raw
            h = q.get('equipo_local_normalizado', q.get('equipo_local', '')).strip()
            a = q.get('equipo_visitante_normalizado', q.get('equipo_visitante', '')).strip()
            
            # Normalización extra: minusculas y sin acentos
            h_norm = remove_accents(h).lower()
            a_norm = remove_accents(a).lower()
            
            quiniela_pairs.append({'h_raw': h, 'a_raw': a, 'h_norm': h_norm, 'a_norm': a_norm, 'found': False})
    else:
        print("ADVERTENCIA: No se encontró fichero de Quiniela. Se analizarán TODOS los partidos próximos.")

    predictions = [] # Reset predictions list for the definitive pass
    
    for m in upcoming_matches_raw:
        # Filtrado por Quiniela
        if quiniela_matches:
            # Normalización del partido actual
            current_home = remove_accents(m['home_team_name'].strip()).lower()
            current_away = remove_accents(m['away_team_name'].strip()).lower()
            
            # Búsqueda directa
            found_match_idx = -1
            for idx, q_item in enumerate(quiniela_pairs):
                qh = q_item['h_norm']
                qa = q_item['a_norm']
                
                # Comparamos si un string está contenido en otro para mayor flexibilidad
                # Ej: "alaves" in "deportivo alaves" (True)
                # Ej: "racing s." -> "racing s" vs "racing de santander" (Fail? Need checks)
                
                # Check Local
                home_match = (qh in current_home) or (current_home in qh)
                # Check Visitante
                away_match = (qa in current_away) or (current_away in qa)
                
                # Special cases matching hacks if needed
                if not home_match and "racing" in qh and "racing" in current_home: home_match = True # Danger but pragmatic
                if not away_match and "racing" in qa and "racing" in current_away: away_match = True

                if home_match and away_match:
                    found_match_idx = idx
                    break
            
            if found_match_idx == -1:
                continue
                
            # Marcar como encontrado para reporte final
            quiniela_pairs[found_match_idx]['found'] = True

        try:
            match_obj = Match(
                id=m['id'],
                home_team=Team(id=m['home_team_id'], name=m['home_team_name']),
                away_team=Team(id=m['away_team_id'], name=m['away_team_name']),
                date=datetime.fromisoformat(m['date']),
                league=m.get('league', 'Unknown'),
                venue=None, # Venue scraping pendiente
            )

            # --- Detección de Anomalías Logísticas (Neutral Ground) ---
            # Si news_data["logistic_issues"] contiene términos de campo neutral
            # y es relevante para el partido actual, se actualiza match_obj.venue
            home_team_lower = match_obj.home_team.name.lower()
            away_team_lower = match_obj.away_team.name.lower()

            for issue_entry in logistic_issues:
                issue_text = issue_entry.get('issue', '').lower()
                issue_source = issue_entry.get('source', '').lower()

                # Check for neutral ground terms within the issue itself
                is_neutral_term = any(term in issue_text for term in NEUTRAL_GROUND_TERMS)

                # Check for team names in the issue context or source to ensure relevance
                is_relevant = (home_team_lower in issue_text or away_team_lower in issue_text or
                               home_team_lower in issue_source or away_team_lower in issue_source)
                
                # If a neutral ground term is found and it's relevant to this match,
                # set the venue to signal predictor.py
                if is_neutral_term and is_relevant:
                    match_obj.venue = issue_text # Or "neutral ground"
                    print(f"    ¡Anomalía logística detectada! Partido en {match_obj.venue} (Posible campo neutral)")
                    break # Only need to find one relevant issue

            # Obtener datos clima (Simulado/Mockeado si no hay API Key)
            # Para demo, asumimos que juegan en la 'ciudad' del equipo local
            city = match_obj.home_team.name 
            weather_data = weather_client.get_forecast(city, match_obj.date)

            # Datos jugadores (Scraping de bajas y alineaciones/plantilla)
            print(f"  Obteniendo info jugadores para {match_obj.home_team.name} vs {match_obj.away_team.name}...")
            lineups_data = scraper.get_match_lineups(match_obj.id)
            
            home_missing = parse_players(lineups_data, 'home', 'missingPlayers')
            away_missing = parse_players(lineups_data, 'away', 'missingPlayers')
            
            # Intentamos sacar la alineación titular ("players")
            home_squad = parse_players(lineups_data, 'home', 'players')
            away_squad = parse_players(lineups_data, 'away', 'players')
            
            # Identificar jugadores clave del equipo (Top N por rating)
            home_key_players = _get_top_n_players_by_rating(home_squad, n=3)
            away_key_players = _get_top_n_players_by_rating(away_squad, n=3)
            
            if home_missing:
                print(f"    Bajas Local: {len(home_missing)}")
            if away_missing:
                print(f"    Bajas Visitante: {len(away_missing)}")
                
            if home_squad:
                print(f"    Plantilla Local Disponible: {len(home_squad)}")
            if away_squad:
                print(f"    Plantilla Visitante Disponible: {len(away_squad)}")
            if home_key_players:
                print(f"    Jugadores Clave Local: {[p.name for p in home_key_players]}")
            if away_key_players:
                print(f"    Jugadores Clave Visitante: {[p.name for p in away_key_players]}")

            # Obtener porcentajes de Losilla si este partido está en la quiniela
            losilla_percentages = None
            if quiniela_matches and found_match_idx != -1:
                # Buscar el número de partido en la quiniela para obtener los porcentajes de Losilla
                quiniela_match_num = found_match_idx + 1  # Los índices son 0-based, números de partido 1-based
                if quiniela_match_num in losilla_data:
                    losilla_percentages = losilla_data[quiniela_match_num]

            prediction = predictor.predict(
                match=match_obj,
                weather_data=weather_data,
                home_players=home_missing, 
                away_players=away_missing,
                home_lineup=home_squad,
                away_lineup=away_squad,
                home_key_players=home_key_players, # Pasar jugadores clave
                away_key_players=away_key_players, # Pasar jugadores clave
                global_matches=global_matches,
                losilla_percentages=losilla_percentages
            )
            
            # Guardamos el índice de la quiniela para ordenar después si es necesario
            pred_entry = {'prediction': prediction, 'quiniela_index': found_match_idx if quiniela_matches else 999}
            predictions.append(pred_entry)
        except (KeyError, TypeError) as e:
            print(f"Error procesando partido {m.get('id')}: {e}")
            continue

    # Ordenar por el orden de la quiniela (índice 0, 1, 2...)
    if quiniela_matches and predictions:
        print("Ordenando resultados según el orden de la Quiniela...")
        predictions.sort(key=lambda x: x['quiniela_index'])

    # Guardar resultados
    output_path = PROCESSED_DATA_DIR / "upcoming_match_predictions.json"
    
    # Convertir a formato serializable
    output_data = []
    for item in predictions:
        p = item['prediction']
        # Añadir número de quiniela si está disponible
        q_num = item['quiniela_index'] + 1 if quiniela_matches and item['quiniela_index'] != 999 else None
        
        data_obj = {
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
        
        if q_num:
            data_obj["quiniela_match_number"] = q_num
        
        # Incluir datos de Losilla si están disponibles en los factores
        if p.factors and "losilla_data" in p.factors:
            data_obj["losilla_data"] = p.factors["losilla_data"]
            
        output_data.append(data_obj)

    save_mongo_data("upcoming_match_predictions", output_data)

    print(f"Generación de predicciones completada. Resultados guardados en MongoDB (upcoming_match_predictions)")
    
    if quiniela_matches:
        print("\n--- Resumen de Cobertura Quiniela ---")
        missing_count = 0
        for q in quiniela_pairs:
            if not q['found']:
                print(f"FALTANTE: {q['h_raw']} vs {q['a_raw']}")
                missing_count += 1
        
        if missing_count == 0:
            print("¡Todos los partidos de la Quiniela fueron encontrados y analizados!")
        else:
            print(f"Total faltantes: {missing_count}. Verifique nombres o si los partidos ya se jugaron/no están en el calendario próximo.")

if __name__ == "__main__":
    main()
