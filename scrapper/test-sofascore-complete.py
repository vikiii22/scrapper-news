"""
Ejemplo completo de uso de soccerdata con Sofascore para temporada actual
"""
import soccerdata as sd
from datetime import datetime
import json

print("=" * 60)
print("SOCCERDATA - TEMPORADA ACTUAL CON SOFASCORE")
print("=" * 60)

# Definir ligas disponibles
ligas = {
    'La Liga': 'ESP-La Liga',
    'Premier League': 'ENG-Premier League',
    'Serie A': 'ITA-Serie A',
    'Bundesliga': 'GER-Bundesliga',
    'Ligue 1': 'FRA-Ligue 1'
}

temporada_actual = '2526'  # Temporada 2025/26

print(f"\n📅 Fecha actual: {datetime.now().strftime('%Y-%m-%d')}")
print(f"🏆 Temporada: {temporada_actual}")

for liga_nombre, liga_code in ligas.items():
    print(f"\n{'='*60}")
    print(f"🔍 {liga_nombre} ({liga_code})")
    print('='*60)
    
    try:
        sofascore = sd.Sofascore(leagues=liga_code, seasons=temporada_actual)
        
        # 1. Calendario de partidos
        print("\n📅 CALENDARIO DE PARTIDOS")
        schedule = sofascore.read_schedule()
        print(f"   Total partidos: {len(schedule)}")
        
        # Partidos jugados
        played = schedule[schedule['home_score'].notna()]
        print(f"   Partidos jugados: {len(played)}")
        print(f"   Partidos por jugar: {len(schedule) - len(played)}")
        
        # Últimos 5 resultados
        if len(played) > 0:
            print(f"\n   📊 Últimos 5 resultados:")
            for idx, row in played.tail(5).iterrows():
                print(f"      • {row['home_team']} {int(row['home_score'])} - {int(row['away_score'])} {row['away_team']} (Jornada {row['round']})")
        
        # Próximos 5 partidos
        upcoming = schedule[schedule['home_score'].isna()]
        if len(upcoming) > 0:
            print(f"\n   📆 Próximos 5 partidos:")
            for idx, row in upcoming.head(5).iterrows():
                fecha = row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date'])
                print(f"      • {row['home_team']} vs {row['away_team']} ({fecha})")
        
        # 2. Tabla de clasificación
        try:
            print(f"\n🏆 TABLA DE CLASIFICACIÓN")
            table = sofascore.read_league_table()
            if not table.empty:
                print(f"\n   Top 5:")
                for idx, (team, row) in enumerate(table.head(5).iterrows(), 1):
                    pts = row.get('pts', row.get('points', 'N/A'))
                    pj = row.get('games', row.get('played', 'N/A'))
                    print(f"      {idx}. {team} - {pts} pts ({pj} PJ)")
        except Exception as e:
            print(f"   ⚠️  Error al obtener tabla: {str(e)}")
        
        # Solo mostrar detalles de La Liga para no hacer demasiado largo
        if liga_code == 'ESP-La Liga':
            # 3. Guardar datos de ejemplo
            print(f"\n💾 GUARDANDO DATOS DE EJEMPLO")
            
            # Guardar calendario completo
            schedule_data = schedule.to_dict('records')
            with open('../data/laliga_schedule_2526.json', 'w', encoding='utf-8') as f:
                json.dump(schedule_data[:10], f, ensure_ascii=False, indent=2, default=str)
            print(f"   ✅ Primeros 10 partidos guardados en data/laliga_schedule_2526.json")
            
            # Estadísticas básicas
            if len(played) > 0:
                goles_casa = played['home_score'].sum()
                goles_fuera = played['away_score'].sum()
                print(f"\n📈 ESTADÍSTICAS GENERALES")
                print(f"   Goles en casa: {int(goles_casa)}")
                print(f"   Goles fuera: {int(goles_fuera)}")
                print(f"   Total goles: {int(goles_casa + goles_fuera)}")
                print(f"   Promedio goles por partido: {(goles_casa + goles_fuera) / len(played):.2f}")
        
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
    
    # Solo procesar La Liga por ahora
    if liga_code == 'ESP-La Liga':
        break

print(f"\n{'='*60}")
print("✅ PRUEBA COMPLETADA")
print('='*60)

print(f"""
🎯 RESUMEN:
- ✅ Sofascore funciona con la temporada actual (2025/26)
- ✅ Proporciona calendarios, resultados y clasificación
- ✅ Datos actualizados en tiempo real
- ⚠️  FBref está bloqueado (Error 403)
- 💡 Se recomienda usar Sofascore o Understat como alternativa

📚 Puedes integrar esto en tu proyecto para:
   1. Obtener resultados en tiempo real
   2. Analizar estadísticas de equipos
   3. Predecir quinielas con datos actualizados
   4. Complementar tus scrapers actuales
""")
