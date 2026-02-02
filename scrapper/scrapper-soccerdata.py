"""
Ejemplo de integración de soccerdata en tu proyecto actual
Obtiene resultados actualizados de La Liga y Segunda División temporada 2025/26
"""
import soccerdata as sd
from datetime import datetime
import json
import os

# Obtener el directorio base del proyecto (un nivel arriba de scrapper/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')

# Crear directorio data si no existe
os.makedirs(DATA_DIR, exist_ok=True)

def obtener_datos_liga(liga_nombre, liga_code, temporada='2526'):
    """
    Obtiene los resultados, próximos partidos y clasificación de una liga
    """
    print(f"🏆 Obteniendo datos de {liga_nombre} {temporada[:2]}/{temporada[2:]} con Sofascore...")
    
    try:
        # Inicializar Sofascore para la liga
        sofascore = sd.Sofascore(leagues=liga_code, seasons=temporada)
        
        # Obtener calendario completo
        schedule = sofascore.read_schedule()
        
        # Separar partidos jugados y por jugar
        played = schedule[schedule['home_score'].notna()].copy()
        upcoming = schedule[schedule['home_score'].isna()].copy()
        
        print(f"✅ {len(schedule)} partidos en total")
        print(f"   📊 {len(played)} partidos jugados")
        print(f"   📆 {len(upcoming)} partidos por jugar")
        
        # Preparar datos para guardar
        resultados = {
            'fecha_actualizacion': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'temporada': f'20{temporada[:2]}/{temporada[2:]}',
            'liga': liga_nombre,
            'liga_code': liga_code,
            'total_partidos': len(schedule),
            'partidos_jugados': len(played),
            'partidos_pendientes': len(upcoming),
            'ultimos_resultados': [],
            'proximos_partidos': [],
            'clasificacion': [],
            'estadisticas_generales': {}
        }
        
        # Últimos 10 resultados
        for idx, row in played.tail(10).iterrows():
            resultados['ultimos_resultados'].append({
                'jornada': int(row['round']),
                'fecha': str(row['date']),
                'equipo_local': row['home_team'],
                'equipo_visitante': row['away_team'],
                'goles_local': int(row['home_score']),
                'goles_visitante': int(row['away_score']),
                'resultado': f"{int(row['home_score'])}-{int(row['away_score'])}"
            })
        
        # Próximos 10 partidos
        for idx, row in upcoming.head(10).iterrows():
            resultados['proximos_partidos'].append({
                'jornada': int(row['round']),
                'fecha': str(row['date']),
                'equipo_local': row['home_team'],
                'equipo_visitante': row['away_team']
            })
        
        # Obtener tabla de clasificación
        try:
            print(f"   ├─ Obteniendo clasificación...")
            table = sofascore.read_league_table()
            
            if not table.empty:
                print(f"   ├─ ✅ {len(table)} equipos en la clasificación")
                
                # Resetear el índice para obtener los nombres de equipos correctamente
                table_reset = table.reset_index()
                
                for idx, row in table_reset.iterrows():
                    # Obtener el nombre del equipo
                    team_name = row.get('team', row.get('index', 'Unknown'))
                    
                    # Extraer estadísticas básicas
                    ganados = int(row.get('wins', row.get('W', row.get('G', 0))))
                    empatados = int(row.get('draws', row.get('D', row.get('E', 0))))
                    perdidos = int(row.get('losses', row.get('L', row.get('P', 0))))
                    
                    # Calcular partidos jugados
                    partidos_jugados = ganados + empatados + perdidos
                    
                    # Calcular puntos (victorias * 3 + empates * 1)
                    puntos = (ganados * 3) + empatados
                    
                    # Extraer estadísticas del equipo
                    equipo_data = {
                        'posicion': idx + 1,
                        'equipo': str(team_name),
                        'puntos': puntos,
                        'partidos_jugados': partidos_jugados,
                        'ganados': ganados,
                        'empatados': empatados,
                        'perdidos': perdidos,
                        'goles_favor': int(row.get('goals_for', row.get('GF', 0))),
                        'goles_contra': int(row.get('goals_against', row.get('GA', 0))),
                        'diferencia_goles': int(row.get('goal_difference', row.get('GD', 0)))
                    }
                    
                    # Calcular estadísticas adicionales para análisis
                    if partidos_jugados > 0:
                        equipo_data['porcentaje_victorias'] = round((equipo_data['ganados'] / partidos_jugados) * 100, 2)
                        equipo_data['promedio_goles_favor'] = round(equipo_data['goles_favor'] / partidos_jugados, 2)
                        equipo_data['promedio_goles_contra'] = round(equipo_data['goles_contra'] / partidos_jugados, 2)
                        equipo_data['puntos_por_partido'] = round(equipo_data['puntos'] / partidos_jugados, 2)
                    else:
                        equipo_data['porcentaje_victorias'] = 0
                        equipo_data['promedio_goles_favor'] = 0
                        equipo_data['promedio_goles_contra'] = 0
                        equipo_data['puntos_por_partido'] = 0
                    
                    resultados['clasificacion'].append(equipo_data)
            else:
                print(f"   ├─ ⚠️  No hay tabla de clasificación disponible")
                
        except Exception as e:
            print(f"   ├─ ⚠️  Error al obtener clasificación: {str(e)}")
        
        # Estadísticas generales
        if len(played) > 0:
            goles_casa = played['home_score'].sum()
            goles_fuera = played['away_score'].sum()
            total_goles = goles_casa + goles_fuera
            
            resultados['estadisticas_generales'] = {
                'total_goles': int(total_goles),
                'goles_en_casa': int(goles_casa),
                'goles_fuera': int(goles_fuera),
                'promedio_goles_partido': round(total_goles / len(played), 2),
                'victorias_local': int(len(played[played['home_score'] > played['away_score']])),
                'empates': int(len(played[played['home_score'] == played['away_score']])),
                'victorias_visitante': int(len(played[played['home_score'] < played['away_score']]))
            }
        
        # Guardar en archivo JSON
        filename = f"{liga_code.lower().replace('-', '_').replace(' ', '_')}_resultados.json"
        output_path = os.path.join(DATA_DIR, filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(resultados, f, ensure_ascii=False, indent=2)
        
        print(f"   └─ ✅ Guardado en: {filename}")
        
        return resultados
        
    except Exception as e:
        print(f"   └─ ❌ Error: {str(e)}")
        return None


def obtener_resultados_laliga_actual():
    """
    Obtiene los resultados y próximos partidos de La Liga actual usando soccerdata
    """
    return obtener_datos_liga('La Liga', 'ESP-La Liga', '2526')


def obtener_resultados_segunda_division():
    """
    Obtiene los resultados y próximos partidos de la Segunda División española
    """
    return obtener_datos_liga('Segunda División', 'ESP-Segunda División', '2526')


def obtener_datos_completos_espana():
    """
    Obtiene datos completos de Primera y Segunda División española
    """
    print("=" * 60)
    print("OBTENIENDO DATOS COMPLETOS DEL FÚTBOL ESPAÑOL")
    print("=" * 60)
    
    datos_completos = {
        'fecha_actualizacion': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'temporada': '2025/26',
        'ligas': {}
    }
    
    # La Liga (Primera División)
    print("\n📊 PRIMERA DIVISIÓN (LA LIGA)")
    print("-" * 60)
    laliga = obtener_resultados_laliga_actual()
    if laliga:
        datos_completos['ligas']['primera_division'] = laliga
    
    # Segunda División
    print("\n\n📊 SEGUNDA DIVISIÓN")
    print("-" * 60)
    segunda = obtener_resultados_segunda_division()
    if segunda:
        datos_completos['ligas']['segunda_division'] = segunda
    
    # Guardar datos completos
    output_path = os.path.join(DATA_DIR, 'futbol_espanol_completo.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(datos_completos, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*60}")
    print(f"✅ DATOS COMPLETOS GUARDADOS EN: futbol_espanol_completo.json")
    print('='*60)
    
    # Mostrar resumen
    if laliga and segunda:
        print(f"""
📈 RESUMEN ESPAÑA:

PRIMERA DIVISIÓN:
  • Partidos jugados: {laliga['partidos_jugados']}/{laliga['total_partidos']}
  • Promedio goles: {laliga['estadisticas_generales']['promedio_goles_partido']} por partido
  • Equipos en clasificación: {len(laliga['clasificacion'])}

SEGUNDA DIVISIÓN:
  • Partidos jugados: {segunda['partidos_jugados']}/{segunda['total_partidos']}
  • Promedio goles: {segunda['estadisticas_generales']['promedio_goles_partido']} por partido
  • Equipos en clasificación: {len(segunda['clasificacion'])}
""")
    
    return datos_completos


def obtener_resultados_multiples_ligas():
    """
    Obtiene resultados de múltiples ligas europeas
    """
    ligas = {
        'La Liga': 'ESP-La Liga',
        'Premier League': 'ENG-Premier League',
        'Serie A': 'ITA-Serie A',
        'Bundesliga': 'GER-Bundesliga',
        'Ligue 1': 'FRA-Ligue 1'
    }
    
    todos_resultados = {}
    
    for liga_nombre, liga_code in ligas.items():
        print(f"\n🔍 Procesando {liga_nombre}...")
        try:
            sofascore = sd.Sofascore(leagues=liga_code, seasons='2526')
            schedule = sofascore.read_schedule()
            played = schedule[schedule['home_score'].notna()]
            
            todos_resultados[liga_nombre] = {
                'total_partidos': len(schedule),
                'partidos_jugados': len(played),
                'ultimos_5_resultados': []
            }
            
            for idx, row in played.tail(5).iterrows():
                todos_resultados[liga_nombre]['ultimos_5_resultados'].append({
                    'fecha': str(row['date']),
                    'local': row['home_team'],
                    'visitante': row['away_team'],
                    'resultado': f"{int(row['home_score'])}-{int(row['away_score'])}"
                })
            
            print(f"   ✅ {len(played)} partidos jugados")
            
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
    
    # Guardar todos los resultados
    output_path = os.path.join(DATA_DIR, 'ligas_europeas_resultados.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(todos_resultados, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Resultados de todas las ligas guardados en: ligas_europeas_resultados.json")
    return todos_resultados


if __name__ == "__main__":
    print("=" * 60)
    print("SOCCERDATA - INTEGRACIÓN CON TU PROYECTO")
    print("=" * 60)
    
    # Opción 1: Datos completos de España (Primera y Segunda División)
    print("\n📊 OPCIÓN 1: Datos Completos de España (Primera + Segunda)")
    print("-" * 60)
    obtener_datos_completos_espana()
    
    # Opción 2: Múltiples ligas europeas
    print("\n\n📊 OPCIÓN 2: Múltiples Ligas Europeas")
    print("-" * 60)
    obtener_resultados_multiples_ligas()
    
    print("\n" + "=" * 60)
    print("✅ PROCESO COMPLETADO")
    print("=" * 60)
    
    print("""
💡 ARCHIVOS GENERADOS:

1. futbol_espanol_completo.json - Primera y Segunda División con clasificaciones
2. esp_la_liga_resultados.json - Detalles completos de La Liga
3. esp_segunda_división_resultados.json - Detalles completos de Segunda División
4. ligas_europeas_resultados.json - Resumen de ligas europeas

📊 ANÁLISIS DE PROBABILIDADES:

Con la clasificación puedes analizar:
- Posición en la tabla → Fortaleza del equipo
- Promedio de goles a favor → Capacidad ofensiva
- Promedio de goles en contra → Solidez defensiva
- Porcentaje de victorias → Consistencia
- Puntos por partido → Rendimiento general
- Diferencia de goles → Balance del equipo

🎯 PRÓXIMOS PASOS:

1. Usa estos datos para predecir resultados
2. Compara equipos locales vs visitantes
3. Analiza tendencias recientes (últimos 5 partidos)
4. Considera la posición en la tabla
5. Evalúa promedios de goles para estimar marcadores
""")
