"""
Script de prueba para verificar si soccerdata obtiene datos de la temporada actual (2025/26)
"""
import soccerdata as sd
from datetime import datetime

print("=" * 60)
print("PRUEBA DE SOCCERDATA - TEMPORADA ACTUAL 2025/26")
print("=" * 60)

# Obtener la temporada actual (estamos en febrero 2026, así que la temporada es 2025/26)
current_season = '2526'  # Formato de soccerdata para temporada 2025/26

ligas = {
    'Premier League': 'ENG-Premier League',
    'La Liga': 'ESP-La Liga',
    'Serie A': 'ITA-Serie A',
    'Bundesliga': 'GER-Bundesliga',
    'Ligue 1': 'FRA-Ligue 1'
}

print(f"\n📅 Fecha actual: {datetime.now().strftime('%Y-%m-%d')}")
print(f"🏆 Temporada a consultar: {current_season}")
print("\n" + "=" * 60)

# Probar con FBref (una de las fuentes más completas)
for liga_nombre, liga_code in ligas.items():
    print(f"\n🔍 Probando {liga_nombre} ({liga_code})...")
    try:
        # Sintaxis correcta: FBref(leagues, seasons)
        fbref = sd.FBref(leagues=liga_code, seasons=current_season)
        
        # Intentar obtener el calendario de partidos
        print(f"   ├─ Obteniendo calendario...")
        schedule = fbref.read_schedule()
        
        if not schedule.empty:
            print(f"   ├─ ✅ {len(schedule)} partidos encontrados")
            print(f"   ├─ Columnas disponibles: {list(schedule.columns)}")
            
            # Mostrar los últimos 3 partidos como muestra
            if len(schedule) > 0:
                print(f"   └─ Últimos 3 partidos:")
                for idx, row in schedule.tail(3).iterrows():
                    print(f"      • {row.get('home_team', 'N/A')} vs {row.get('away_team', 'N/A')}")
        else:
            print(f"   └─ ⚠️  No hay datos disponibles aún para esta temporada")
            
    except Exception as e:
        print(f"   └─ ❌ Error: {str(e)}")

print("\n" + "=" * 60)
print("\n🔍 Probando temporada anterior (2024/25) para comparar...")

try:
    fbref_anterior = sd.FBref(leagues='ESP-La Liga', seasons='2425')
    schedule_anterior = fbref_anterior.read_schedule()
    print(f"✅ Temporada 2024/25: {len(schedule_anterior)} partidos encontrados")
    
    # Obtener estadísticas de equipos
    print("\n📊 Probando estadísticas de equipos temporada 2024/25...")
    team_stats = fbref_anterior.read_team_season_stats()
    print(f"✅ Estadísticas de {len(team_stats)} equipos obtenidas")
    print(f"   Columnas disponibles: {list(team_stats.columns[:10])}...")
    
except Exception as e:
    print(f"❌ Error con temporada anterior: {str(e)}")

print("\n" + "=" * 60)
print("PRUEBA COMPLETADA")
print("=" * 60)
