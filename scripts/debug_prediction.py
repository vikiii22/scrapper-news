
import sys
from pathlib import Path
import json

# Configurar sys.path
project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))
sys.path.append(str(project_root / 'src'))

from config.settings import PROCESSED_DATA_DIR, RAW_DATA_DIR
from utils.data_loader import load_json_data
from analysis.predictor import PredictionEngine
from models.match import Match, Team
from datetime import datetime

def debug_match():
    # Cargar datos
    la_liga_matches = load_json_data(RAW_DATA_DIR / "la_liga_all_matches.json") or []
    segunda_matches = load_json_data(RAW_DATA_DIR / "segunda_all_matches.json") or []
    historical_matches_raw = la_liga_matches + segunda_matches
    
    historical_matches = []
    for m in historical_matches_raw:
        try:
            historical_matches.append(Match(
                id=m['id'],
                home_team=Team(id=m['home_team_id'], name=m['home_team_name']),
                away_team=Team(id=m['away_team_id'], name=m['away_team_name']),
                date=datetime.fromisoformat(m['date']),
                league=m.get('league', 'Unknown'),
                home_score=m.get('home_score'),
                away_score=m.get('away_score')
            ))
        except: continue

    engine = PredictionEngine(historical_matches=historical_matches, standings=[])
    
    # Simular partido Oviedo vs Athletic
    match = Match(
        id=0,
        home_team=Team(id=0, name="Real Oviedo"),
        away_team=Team(id=0, name="Athletic Club"),
        date=datetime.now(),
        league="La Liga"
    )
    
    print("\n--- DEBUG OVIEDO vs ATHLETIC ---")
    
    # Calcular factores individuales
    from analysis.factors import home_away, form, h2h
    
    print("\n1. Factor Local/Visitante:")
    h_factor = home_away.calculate_home_away_factor("Real Oviedo", historical_matches, True)
    a_factor = home_away.calculate_home_away_factor("Athletic Club", historical_matches, False)
    print(f"Oviedo (Casa): {h_factor}")
    print(f"Athletic (Fuera): {a_factor}")
    
    print("\n2. Factor Forma (últimos 5):")
    f_factor = form.calculate_form_factor("Real Oviedo", "Athletic Club", historical_matches)
    print(f"Diferencia de forma: {f_factor}")
    
    print("\n3. Predicción completa:")
    pred = engine.predict(match)
    print(json.dumps(pred.factors, indent=2))
    print(f"Probabilidades: 1: {pred.prob_home} X: {pred.prob_draw} 2: {pred.prob_away}")

if __name__ == "__main__":
    debug_match()
