"""
Ejemplo de integración de soccerdata en tu proyecto actual
Obtiene resultados actualizados de La Liga temporada 2025/26
"""
import soccerdata as sd
from datetime import datetime
import json
import os

def obtener_resultados_laliga_actual():
    """
    Obtiene los resultados y próximos partidos de La Liga actual usando soccerdata
    """
    print("🏆 Obteniendo datos de La Liga 2025/26 con Sofascore...")
    
    try:
        # Inicializar Sofascore para La Liga temporada actual
        sofascore = sd.Sofascore(leagues='ESP-La Liga', seasons='2526')
        
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
            'temporada': '2025/26',
            'liga': 'La Liga',
            'total_partidos': len(schedule),
            'partidos_jugados': len(played),
            'partidos_pendientes': len(upcoming),
            'ultimos_resultados': [],
            'proximos_partidos': [],
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
        output_path = os.path.join('data', 'laliga_resultados_actuales.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(resultados, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ Datos guardados en: {output_path}")
        
        return resultados
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None

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
    output_path = os.path.join('data', 'ligas_europeas_resultados.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(todos_resultados, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Resultados de todas las ligas guardados en: {output_path}")
    return todos_resultados

if __name__ == "__main__":
    print("=" * 60)
    print("SOCCERDATA - INTEGRACIÓN CON TU PROYECTO")
    print("=" * 60)
    
    # Opción 1: Solo La Liga
    print("\n📊 OPCIÓN 1: Solo La Liga")
    print("-" * 60)
    obtener_resultados_laliga_actual()
    
    # Opción 2: Múltiples ligas
    print("\n\n📊 OPCIÓN 2: Múltiples Ligas Europeas")
    print("-" * 60)
    obtener_resultados_multiples_ligas()
    
    print("\n" + "=" * 60)
    print("✅ PROCESO COMPLETADO")
    print("=" * 60)
    
    print("""
💡 CÓMO USAR ESTO EN TU PROYECTO:

1. ACTUALIZAR RESULTADOS DIARIOS:
   - Ejecuta este script automáticamente cada día
   - Los datos se guardan en data/laliga_resultados_actuales.json
   
2. INTEGRAR CON TU ANÁLISIS DE QUINIELAS:
   - Importa los datos actualizados en scrapper-analysis.py
   - Usa las estadísticas para mejorar predicciones
   
3. COMPLEMENTAR TUS SCRAPERS:
   - Combina con scrapper-results.py
   - Valida datos con múltiples fuentes
   
4. EJEMPLO DE USO:
   
   from scrapper.scrapper-soccerdata import obtener_resultados_laliga_actual
   
   # Obtener datos actualizados
   datos = obtener_resultados_laliga_actual()
   
   # Usar en tu análisis
   if datos:
       print(f"Promedio de goles: {datos['estadisticas_generales']['promedio_goles_partido']}")
""")
