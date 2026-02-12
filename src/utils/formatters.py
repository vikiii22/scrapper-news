"""Utilidades para formatear la salida."""
import json
from typing import List
from src.models.prediction import Prediction

def format_predictions_to_console(predictions: List[Prediction]):
    """Formatea las predicciones para mostrarlas en la consola."""
    for p in predictions:
        print(f"Partido: {p.match.home_team.name} vs {p.match.away_team.name}")
        print(f"  Fecha: {p.match.date.strftime('%Y-%m-%d %H:%M')}")
        print(f"  Predicción: {p.recommended_bet} (Confianza: {p.confidence_level} - {p.confidence:.2f}%)")
        print(f"  Probabilidades: 1: {p.prob_home:.2f}%, X: {p.prob_draw:.2f}%, 2: {p.prob_away:.2f}%")
        print("-" * 20)

def format_predictions_to_json(predictions: List[Prediction]) -> str:
    """Convierte las predicciones a una cadena JSON."""
    output = []
    for p in predictions:
        output.append({
            "match_id": p.match.id,
            "home_team": p.match.home_team.name,
            "away_team": p.match.away_team.name,
            "date": p.match.date.isoformat(),
            "prediction": p.recommended_bet,
            "confidence": p.confidence,
            "confidence_level": p.confidence_level,
            "probabilities": {
                "home": p.prob_home,
                "draw": p.prob_draw,
                "away": p.prob_away,
            },
            "factors": p.factors,
        })
    return json.dumps(output, indent=4, ensure_ascii=False)
