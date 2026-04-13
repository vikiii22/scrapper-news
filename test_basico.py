#!/usr/bin/env python3
"""
test_basico.py - Tests básicos para verificar componentes de Quiniela Pro
"""

import sys
from pathlib import Path

# Añadir directorio actual al path para importar quiniela_pro
sys.path.insert(0, str(Path(__file__).parent))

from quiniela_pro import (
    Match, TeamStats, StatisticalModel,
    CONFIG, TEAM_NAME_MAPPING, LosillaParser
)
import numpy as np


def test_team_name_mapping():
    """Verifica que el mapeo de nombres funciona"""
    print("🧪 Test 1: Mapeo de nombres de equipos")
    
    parser = LosillaParser("http://example.com", TEAM_NAME_MAPPING)
    
    test_cases = [
        ("AT.MADRID", "Ath Madrid"),
        ("BARÇA", "Barcelona"),
        ("R.MADRID", "Real Madrid"),
        ("ATHLETIC", "Ath Bilbao"),
        ("Desconocido", "Desconocido"),  # Debe devolver el original
    ]
    
    for input_name, expected in test_cases:
        result = parser.normalize_team_name(input_name)
        status = "✓" if result == expected else "✗"
        print(f"  {status} {input_name:20s} → {result:15s} (esperado: {expected})")
    
    print()


def test_match_creation():
    """Verifica creación de objetos Match"""
    print("🧪 Test 2: Creación de objetos Match")
    
    match = Match(home_team="Barcelona", away_team="Real Madrid")
    
    checks = [
        ("home_team", match.home_team == "Barcelona"),
        ("away_team", match.away_team == "Real Madrid"),
        ("probs iniciales", match.home_prob == 0.0),
        ("prediction inicial", match.prediction == ''),
    ]
    
    for name, passed in checks:
        status = "✓" if passed else "✗"
        print(f"  {status} {name}")
    
    print()


def test_statistical_model():
    """Verifica el modelo estadístico básico"""
    print("🧪 Test 3: Modelo estadístico")
    
    model = StatisticalModel(CONFIG)
    
    # Crear estadísticas de equipos de prueba
    model.team_stats = {
        'Barcelona': TeamStats(attack_strength=1.5, defense_strength=0.7, home_advantage=1.2),
        'Getafe': TeamStats(attack_strength=0.8, defense_strength=1.1, home_advantage=1.2),
    }
    model.league_avg_goals = 1.5
    
    # Predecir partido
    match = Match(home_team="Barcelona", away_team="Getafe")
    predicted = model.predict_match(match)
    
    checks = [
        ("Prob 1 calculada", predicted.home_prob > 0),
        ("Prob X calculada", predicted.draw_prob > 0),
        ("Prob 2 calculada", predicted.away_prob > 0),
        ("Suma = 1.0", abs(predicted.home_prob + predicted.draw_prob + predicted.away_prob - 1.0) < 0.01),
        ("Predicción asignada", predicted.prediction in ['1', 'X', '2']),
        ("Entropía calculada", 0 <= predicted.entropy <= 2),
        ("Barcelona favorito", predicted.home_prob > predicted.away_prob),  # Barcelona debe ser favorito
    ]
    
    for name, passed in checks:
        status = "✓" if passed else "✗"
        print(f"  {status} {name}")
    
    print(f"\n  Resultado detallado:")
    print(f"    P(1)={predicted.home_prob:.1%}, P(X)={predicted.draw_prob:.1%}, P(2)={predicted.away_prob:.1%}")
    print(f"    Predicción: {predicted.prediction}, Confianza: {predicted.confidence:.1%}")
    print(f"    Entropía: {predicted.entropy:.3f}")
    print()


def test_entropy_calculation():
    """Verifica cálculo de entropía"""
    print("🧪 Test 4: Cálculo de entropía")
    
    model = StatisticalModel(CONFIG)
    
    test_cases = [
        ([1.0, 0.0, 0.0], 0.0, "Certeza total"),
        ([0.5, 0.5, 0.0], 1.0, "Dos opciones equiprobables"),
        ([0.33, 0.33, 0.34], 1.58, "Máxima incertidumbre"),
        ([0.7, 0.2, 0.1], 1.16, "Favorito claro"),
    ]
    
    for probs, expected_entropy, description in test_cases:
        calculated = model._calculate_entropy(probs)
        error = abs(calculated - expected_entropy)
        status = "✓" if error < 0.05 else "✗"
        print(f"  {status} {description:30s}: H={calculated:.2f} (esperado ~{expected_entropy:.2f})")
    
    print()


def test_dixon_coles():
    """Verifica corrección Dixon-Coles"""
    print("🧪 Test 5: Corrección Dixon-Coles")
    
    model = StatisticalModel(CONFIG)
    lambda_h, lambda_a = 1.5, 1.2
    
    test_cases = [
        (0, 0, "Empate 0-0 (debe reducir probabilidad)"),
        (1, 1, "Empate 1-1 (debe reducir probabilidad)"),
        (0, 1, "0-1 (debe aumentar probabilidad)"),
        (1, 0, "1-0 (debe aumentar probabilidad)"),
        (2, 2, "Otro resultado (sin corrección)"),
    ]
    
    for h, a, description in test_cases:
        correction = model.dixon_coles_correction(h, a, lambda_h, lambda_a)
        symbol = "<" if correction < 1.0 else (">" if correction > 1.0 else "=")
        print(f"  {description:35s}: factor={correction:.3f} {symbol} 1.0")
    
    print()


def test_european_adjustments():
    """Verifica ajustes por competición europea"""
    print("🧪 Test 6: Ajustes por competición europea")
    
    model = StatisticalModel(CONFIG)
    model.team_stats = {
        'Barcelona': TeamStats(attack_strength=1.5, defense_strength=0.7),
        'Getafe': TeamStats(attack_strength=0.8, defense_strength=1.1),
    }
    model.league_avg_goals = 1.5
    
    # Predicción sin ajustes
    match1 = Match(home_team="Barcelona", away_team="Getafe")
    pred1 = model.predict_match(match1)
    
    # Predicción con penalización
    model.set_european_adjustments({'Barcelona': -0.15})  # -15% ataque
    match2 = Match(home_team="Barcelona", away_team="Getafe")
    pred2 = model.predict_match(match2)
    
    print(f"  Sin ajuste:   P(1)={pred1.home_prob:.1%}")
    print(f"  Con -15%:     P(1)={pred2.home_prob:.1%}")
    
    reduced = pred2.home_prob < pred1.home_prob
    status = "✓" if reduced else "✗"
    print(f"\n  {status} La penalización reduce P(1): {reduced}")
    print()


def test_time_weighting():
    """Verifica que el decay exponencial funciona"""
    print("🧪 Test 7: Time-weighting (decay exponencial)")
    
    decay = CONFIG['decay_factor']
    positions = [0, 5, 10, 20]
    
    print(f"  Factor de decay: {decay}")
    for pos in positions:
        weight = decay ** pos
        print(f"    Partido hace {pos:2d} jornadas: peso = {weight:.3f}")
    
    # Verificar que decrece
    weights = [decay ** i for i in range(4)]
    decreasing = all(weights[i] > weights[i+1] for i in range(3))
    status = "✓" if decreasing else "✗"
    print(f"\n  {status} Los pesos decrecen correctamente: {decreasing}")
    print()


def run_all_tests():
    """Ejecuta todos los tests"""
    print("\n" + "="*80)
    print("QUINIELA PRO - Suite de Tests Básicos".center(80))
    print("="*80 + "\n")
    
    tests = [
        test_team_name_mapping,
        test_match_creation,
        test_statistical_model,
        test_entropy_calculation,
        test_dixon_coles,
        test_european_adjustments,
        test_time_weighting,
    ]
    
    for test_func in tests:
        try:
            test_func()
        except Exception as e:
            print(f"  ✗ ERROR en {test_func.__name__}: {e}\n")
    
    print("="*80)
    print("Tests completados".center(80))
    print("="*80 + "\n")


if __name__ == "__main__":
    run_all_tests()
