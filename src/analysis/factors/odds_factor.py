"""Factor de cuotas de mercado para ajuste bayesiano de predicciones.

Las cuotas de casas de apuestas representan el consenso de cientos de analistas
y contienen información que los modelos estadísticos puros no capturan (noticias
de última hora, lesiones no confirmadas, historial de squad rotation, etc.).

Este módulo convierte cuotas decimales a probabilidades normalizadas y calcula
un factor de ajuste para el predictor principal.
"""
from typing import Dict, Optional


def calculate_odds_factor(
    market_odds: Dict[str, float]
) -> Dict[str, float]:
    """
    Convierte cuotas del mercado en probabilidades implícitas normalizadas.

    Args:
        market_odds: Cuotas decimales, ej. {"1": 1.45, "X": 4.20, "2": 6.50}

    Returns:
        Dict con probabilidades normalizadas (sin overround) y el overround detectado.
        {
            "prob_1": 63.7,   # % de victoria local (limpio)
            "prob_X": 22.0,   # % de empate (limpio)
            "prob_2": 14.2,   # % de victoria visitante (limpio)
            "overround": 8.1, # % de margen de la casa
            "valid": True
        }
    """
    if not market_odds:
        return {"valid": False}

    try:
        raw = {}
        for sign in ["1", "X", "2"]:
            odd_val = float(market_odds.get(sign, 0))
            if odd_val <= 1.0:
                return {"valid": False, "error": f"Cuota inválida para '{sign}': {odd_val}"}
            raw[sign] = 1.0 / odd_val

        total = sum(raw.values())
        if total <= 0:
            return {"valid": False, "error": "Total de probabilidades brutas es 0"}

        overround_pct = (total - 1.0) * 100

        return {
            "prob_1": round((raw["1"] / total) * 100, 2),
            "prob_X": round((raw["X"] / total) * 100, 2),
            "prob_2": round((raw["2"] / total) * 100, 2),
            "overround": round(overround_pct, 2),
            "valid": True,
        }
    except (TypeError, ValueError, ZeroDivisionError) as e:
        return {"valid": False, "error": str(e)}


def blend_with_model(
    model_probs: Dict[str, float],
    market_odds: Dict[str, float],
    odds_weight: float = 0.25,
) -> Dict[str, float]:
    """
    Mezcla las probabilidades del modelo con las del mercado.

    Fórmula: prob_final = (1 - w) * prob_modelo + w * prob_mercado

    Args:
        model_probs: {"1": 55.0, "X": 28.0, "2": 17.0} — del modelo Poisson+factores.
        market_odds: {"1": 1.45, "X": 4.20, "2": 6.50} — cuotas decimales.
        odds_weight: Peso del mercado (default 0.25 = 25%).

    Returns:
        Probabilidades mezcladas, normalizadas a 100%.
    """
    market_result = calculate_odds_factor(market_odds)
    if not market_result.get("valid"):
        return model_probs  # Si las cuotas son malas, usar solo el modelo

    blended = {}
    for sign, model_key, mkt_key in [
        ("1", "1", "prob_1"),
        ("X", "X", "prob_X"),
        ("2", "2", "prob_2"),
    ]:
        m_prob = float(model_probs.get(sign, 33.33))
        mkt_prob = market_result[mkt_key]
        blended[sign] = (1 - odds_weight) * m_prob + odds_weight * mkt_prob

    # Renormalizar por si hay pequeñas desviaciones de punto flotante
    total = sum(blended.values())
    if total > 0:
        blended = {k: round((v / total) * 100, 2) for k, v in blended.items()}

    return blended
