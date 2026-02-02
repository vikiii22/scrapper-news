"""
Prueba de soccerdata con Understat para temporada actual
"""
import soccerdata as sd
from datetime import datetime
import pandas as pd

print("=" * 60)
print("PRUEBA DE SOCCERDATA - UNDERSTAT")
print("=" * 60)

# Understat tiene datos históricos y actuales muy buenos
ligas = ['EPL', 'La Liga', 'Bundesliga', 'Serie A', 'Ligue 1']

print(f"\n📅 Fecha actual: {datetime.now().strftime('%Y-%m-%d')}")

for liga in ligas:
    print(f"\n🔍 Probando {liga}...")
    try:
        # Understat no requiere temporada en el constructor
        understat = sd.Understat(liga)
        
        # Obtener datos de tiros (incluye xG)
        print(f"   ├─ Obteniendo datos de partidos...")
        shots = understat.read_league_table()
        
        if not shots.empty:
            print(f"   ├─ ✅ {len(shots)} equipos encontrados")
            print(f"   ├─ Columnas: {list(shots.columns)}")
            print(f"   └─ Primeros 3 equipos:")
            for idx, row in shots.head(3).iterrows():
                print(f"      • {idx}")
        else:
            print(f"   └─ ⚠️  No hay datos disponibles")
            
    except Exception as e:
        print(f"   └─ ❌ Error: {str(e)}")

print("\n" + "=" * 60)
print("PROBANDO CLUBELO (Ratings ELO)")
print("=" * 60)

try:
    clubelo = sd.ClubElo()
    print("✅ ClubElo inicializado correctamente")
    
    # Obtener rankings actuales
    print("📊 Obteniendo rankings...")
    rankings = clubelo.read_team_ratings()
    
    print(f"✅ {len(rankings)} equipos con ratings")
    
    # Filtrar equipos españoles
    if 'country' in rankings.columns:
        spanish_teams = rankings[rankings['country'] == 'ESP'].head(10)
        print(f"\n🇪🇸 Top 10 equipos españoles:")
        for idx, row in spanish_teams.iterrows():
            print(f"   • {row.get('team', idx)}: {row.get('elo', 'N/A')}")
    
except Exception as e:
    print(f"❌ Error: {str(e)}")

print("\n" + "=" * 60)
print("PROBANDO SOFASCORE")
print("=" * 60)

try:
    # Sofascore es muy bueno para datos en tiempo real
    sofascore = sd.Sofascore('ESP-La Liga', '2526')
    print("✅ Sofascore inicializado para La Liga 2025/26")
    
    print("📊 Obteniendo calendario...")
    schedule = sofascore.read_schedule()
    
    if not schedule.empty:
        print(f"✅ {len(schedule)} partidos encontrados")
        print(f"Columnas: {list(schedule.columns)}")
    else:
        print("⚠️  Sin datos aún para esta temporada")
        
except Exception as e:
    print(f"❌ Error: {str(e)}")

print("\n" + "=" * 60)
print("PRUEBA COMPLETADA")
print("=" * 60)
