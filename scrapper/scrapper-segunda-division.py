import json
import time
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright

# Configuración de rutas
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR = DATA_DIR / "Sofascore"
(CACHE_DIR / "standings").mkdir(parents=True, exist_ok=True)
(CACHE_DIR / "matches").mkdir(parents=True, exist_ok=True)

TOURNAMENT_ID = 54
SEASON_ID = 77558

def obtener_con_playwright(url, filename, force_refresh=False):
    filepath = CACHE_DIR / filename
    
    # Sistema de caché local
    if filepath.exists() and not force_refresh:
        print(f"Leyendo caché: {filename}")
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)

    with sync_playwright() as p:
        # Lanzamos un navegador real
        browser = p.chromium.launch(headless=True) 
        # Importante: Usar un contexto de navegador normal
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        print(f"Navegando a la API: {url}")
        try:
            # Vamos a la web primero para establecer cookies
            page.goto("https://www.sofascore.com", wait_until="networkidle")
            time.sleep(2)
            
            # Ahora pedimos el JSON directamente
            response = page.goto(url)
            if response.status == 200:
                data = response.json()
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                print(f"✓ Datos guardados en caché: {filename}")
                return data
            else:
                print(f"Error Playwright: {response.status}")
        except Exception as e:
            print(f"Error en navegación: {e}")
        finally:
            browser.close()
    return None


def procesar_clasificacion(data):
    """Procesa los datos de clasificación"""
    if not data or 'standings' not in data:
        return []
    
    clasificacion = []
    rows = data['standings'][0].get('rows', [])
    
    for row in rows:
        team = row.get('team', {})
        ganados = row.get('wins', 0)
        empatados = row.get('draws', 0)
        perdidos = row.get('losses', 0)
        partidos_jugados = row.get('matches', ganados + empatados + perdidos)
        puntos = row.get('points', ganados * 3 + empatados)
        goles_favor = row.get('scoresFor', 0)
        goles_contra = row.get('scoresAgainst', 0)
        
        equipo_data = {
            'posicion': row.get('position', 0),
            'equipo': team.get('name', 'Unknown'),
            'equipo_id': team.get('id', 0),
            'puntos': puntos,
            'partidos_jugados': partidos_jugados,
            'ganados': ganados,
            'empatados': empatados,
            'perdidos': perdidos,
            'goles_favor': goles_favor,
            'goles_contra': goles_contra,
            'diferencia_goles': goles_favor - goles_contra
        }
        
        # Estadísticas adicionales
        if partidos_jugados > 0:
            equipo_data['porcentaje_victorias'] = round((ganados / partidos_jugados) * 100, 2)
            equipo_data['promedio_goles_favor'] = round(goles_favor / partidos_jugados, 2)
            equipo_data['promedio_goles_contra'] = round(goles_contra / partidos_jugados, 2)
            equipo_data['puntos_por_partido'] = round(puntos / partidos_jugados, 2)
        else:
            equipo_data['porcentaje_victorias'] = 0
            equipo_data['promedio_goles_favor'] = 0
            equipo_data['promedio_goles_contra'] = 0
            equipo_data['puntos_por_partido'] = 0
        
        clasificacion.append(equipo_data)
    
    return clasificacion


def procesar_partidos(data):
    """Procesa los datos de partidos"""
    if not data:
        return {'jugados': [], 'pendientes': []}
    
    partidos_jugados = []
    partidos_pendientes = []
    partidos_vistos = set()  # Para evitar duplicados
    
    # El formato es tournamentTeamEvents -> tournament_id -> season_id -> [eventos]
    if 'tournamentTeamEvents' in data:
        for tournament_id, seasons in data['tournamentTeamEvents'].items():
            for season_id, eventos in seasons.items():
                for evento in eventos:
                    # Evitar duplicados usando el ID del evento
                    evento_id = evento.get('id', 0)
                    if evento_id in partidos_vistos:
                        continue
                    partidos_vistos.add(evento_id)
                    
                    home_team = evento.get('homeTeam', {})
                    away_team = evento.get('awayTeam', {})
                    status = evento.get('status', {})
                    home_score = evento.get('homeScore', {})
                    away_score = evento.get('awayScore', {})
                    
                    partido = {
                        'id': evento_id,
                        'jornada': evento.get('roundInfo', {}).get('round', 0),
                        'fecha': datetime.fromtimestamp(evento.get('startTimestamp', 0)).strftime('%Y-%m-%d %H:%M:%S'),
                        'timestamp': evento.get('startTimestamp', 0),
                        'equipo_local': home_team.get('name', 'Unknown'),
                        'equipo_local_id': home_team.get('id', 0),
                        'equipo_visitante': away_team.get('name', 'Unknown'),
                        'equipo_visitante_id': away_team.get('id', 0),
                        'estado': status.get('type', 'unknown')
                    }
                    
                    # Si el partido ya se jugó
                    if status.get('type') == 'finished':
                        partido['goles_local'] = home_score.get('current', 0)
                        partido['goles_visitante'] = away_score.get('current', 0)
                        partido['resultado'] = f"{partido['goles_local']}-{partido['goles_visitante']}"
                        partidos_jugados.append(partido)
                    else:
                        partidos_pendientes.append(partido)
    
    # Ordenar por timestamp
    partidos_jugados.sort(key=lambda x: x['timestamp'])
    partidos_pendientes.sort(key=lambda x: x['timestamp'])
    
    return {
        'jugados': partidos_jugados,
        'pendientes': partidos_pendientes
    }


def generar_estadisticas_generales(partidos_jugados):
    """Genera estadísticas generales"""
    if not partidos_jugados:
        return {}
    
    total_goles = 0
    goles_casa = 0
    goles_fuera = 0
    victorias_local = 0
    empates = 0
    victorias_visitante = 0
    
    for partido in partidos_jugados:
        goles_local = partido.get('goles_local', 0)
        goles_visitante = partido.get('goles_visitante', 0)
        
        total_goles += goles_local + goles_visitante
        goles_casa += goles_local
        goles_fuera += goles_visitante
        
        if goles_local > goles_visitante:
            victorias_local += 1
        elif goles_local < goles_visitante:
            victorias_visitante += 1
        else:
            empates += 1
    
    total_partidos = len(partidos_jugados)
    
    return {
        'total_partidos_jugados': total_partidos,
        'total_goles': total_goles,
        'goles_en_casa': goles_casa,
        'goles_fuera': goles_fuera,
        'promedio_goles_partido': round(total_goles / total_partidos, 2) if total_partidos > 0 else 0,
        'victorias_local': victorias_local,
        'empates': empates,
        'victorias_visitante': victorias_visitante,
        'porcentaje_victorias_local': round((victorias_local / total_partidos) * 100, 2) if total_partidos > 0 else 0,
        'porcentaje_empates': round((empates / total_partidos) * 100, 2) if total_partidos > 0 else 0,
        'porcentaje_victorias_visitante': round((victorias_visitante / total_partidos) * 100, 2) if total_partidos > 0 else 0
    }

def main():
    print("="*60)
    print("SEGUNDA DIVISION ESPANOLA 2025/26")
    print("="*60)
    print("\n--- Iniciando Scraper con Playwright ---\n")
    
    # 1. Obtener clasificación
    print("="*60)
    print("OBTENIENDO CLASIFICACION")
    print("="*60)
    url_clasificacion = f'https://www.sofascore.com/api/v1/unique-tournament/{TOURNAMENT_ID}/season/{SEASON_ID}/standings/total'
    filename_clasificacion = f"standings/tabla_{TOURNAMENT_ID}_{SEASON_ID}.json"
    
    data_clasificacion = obtener_con_playwright(url_clasificacion, filename_clasificacion)
    
    if not data_clasificacion:
        print("ERROR: No se pudo obtener la clasificación")
        return
    
    clasificacion = procesar_clasificacion(data_clasificacion)
    print(f"OK - {len(clasificacion)} equipos procesados")
    
    # Mostrar top 5
    print("\nTOP 5:")
    for i, equipo in enumerate(clasificacion[:5], 1):
        print(f"  {i}. {equipo['equipo']} - {equipo['puntos']} pts ({equipo['partidos_jugados']} PJ)")
    
    # 2. Obtener partidos jugados
    print("\n" + "="*60)
    print("OBTENIENDO PARTIDOS JUGADOS")
    print("="*60)
    url_partidos = f'https://www.sofascore.com/api/v1/unique-tournament/{TOURNAMENT_ID}/season/{SEASON_ID}/team-events/total'
    filename_partidos = f"matches/partidos_{TOURNAMENT_ID}_{SEASON_ID}.json"
    
    data_partidos = obtener_con_playwright(url_partidos, filename_partidos)
    
    if not data_partidos:
        print("ERROR: No se pudieron obtener los partidos")
        return
    
    partidos = procesar_partidos(data_partidos)
    print(f"OK - {len(partidos['jugados'])} partidos jugados")
    
    # 3. Obtener próximos partidos
    print("\n" + "="*60)
    print("OBTENIENDO PROXIMOS PARTIDOS")
    print("="*60)
    url_proximos = f'https://www.sofascore.com/api/v1/unique-tournament/{TOURNAMENT_ID}/season/{SEASON_ID}/events/next/0'
    filename_proximos = f"matches/proximos_{TOURNAMENT_ID}_{SEASON_ID}.json"
    
    data_proximos = obtener_con_playwright(url_proximos, filename_proximos)
    
    if data_proximos:
        partidos_proximos = procesar_partidos(data_proximos)
        # Añadir los partidos pendientes a la lista
        partidos['pendientes'].extend(partidos_proximos['pendientes'])
        print(f"OK - {len(partidos_proximos['pendientes'])} próximos partidos encontrados")
    else:
        print("No se encontraron próximos partidos")
    
    print(f"\nTOTAL: {len(partidos['jugados'])} jugados, {len(partidos['pendientes'])} pendientes")
    
    # Mostrar últimos 5 resultados
    if partidos['jugados']:
        print("\nULTIMOS 5 RESULTADOS:")
        for partido in partidos['jugados'][-5:]:
            print(f"  J{partido['jornada']}: {partido['equipo_local']} {partido['resultado']} {partido['equipo_visitante']}")
    
    # Mostrar próximos 5 partidos
    if partidos['pendientes']:
        print("\nPROXIMOS 5 PARTIDOS:")
        for partido in partidos['pendientes'][:5]:
            print(f"  J{partido['jornada']}: {partido['equipo_local']} vs {partido['equipo_visitante']} ({partido['fecha']})")
    
    # 4. Generar estadísticas
    estadisticas = generar_estadisticas_generales(partidos['jugados'])
    
    # Asegurar que estadisticas tenga valores por defecto
    if not estadisticas:
        estadisticas = {
            'total_partidos_jugados': 0,
            'total_goles': 0,
            'goles_en_casa': 0,
            'goles_fuera': 0,
            'promedio_goles_partido': 0,
            'victorias_local': 0,
            'empates': 0,
            'victorias_visitante': 0,
            'porcentaje_victorias_local': 0,
            'porcentaje_empates': 0,
            'porcentaje_victorias_visitante': 0
        }
    
    # 5. Compilar todo en un JSON final
    datos_completos = {
        'fecha_actualizacion': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'temporada': '2025/26',
        'liga': 'Segunda Division',
        'tournament_id': TOURNAMENT_ID,
        'season_id': SEASON_ID,
        'clasificacion': clasificacion,
        'ultimos_resultados': partidos['jugados'][-10:] if len(partidos['jugados']) >= 10 else partidos['jugados'],
        'proximos_partidos': partidos['pendientes'][:10] if len(partidos['pendientes']) >= 10 else partidos['pendientes'],
        'todos_partidos_jugados': partidos['jugados'],
        'todos_partidos_pendientes': partidos['pendientes'],
        'estadisticas_generales': estadisticas
    }
    
    # 6. Guardar archivo final
    output_path = DATA_DIR / 'segunda_division_completo.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(datos_completos, f, ensure_ascii=False, indent=2)
    
    print("\n" + "="*60)
    print("DATOS GUARDADOS EXITOSAMENTE")
    print("="*60)
    print(f"\nArchivo: segunda_division_completo.json")
    print(f"Ubicacion: {output_path}")
    
    print(f"""
RESUMEN:
  - Equipos en clasificacion: {len(clasificacion)}
  - Partidos jugados: {len(partidos['jugados'])}
  - Partidos pendientes: {len(partidos['pendientes'])}
  - Promedio goles/partido: {estadisticas.get('promedio_goles_partido', 0)}
  - Victorias local: {estadisticas.get('porcentaje_victorias_local', 0)}%
  - Empates: {estadisticas.get('porcentaje_empates', 0)}%
  - Victorias visitante: {estadisticas.get('porcentaje_victorias_visitante', 0)}%

DATOS DISPONIBLES EN EL JSON:
  - clasificacion: Tabla completa con estadisticas por equipo
  - ultimos_resultados: Ultimos 10 partidos jugados
  - proximos_partidos: Proximos 10 partidos
  - todos_partidos_jugados: Lista completa de resultados
  - todos_partidos_pendientes: Lista completa de partidos por jugar
  - estadisticas_generales: Estadisticas globales de la liga
""")

if __name__ == "__main__":
    main()