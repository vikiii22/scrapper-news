"""
Motor de predicción para el predictor de fútbol.

Este módulo combina:

1. Un modelo estadístico simple basado en la distribución de Poisson
   (estándar para estimar goles en fútbol y probabilidades 1X2).

2. Un sistema de explicación del razonamiento, que genera un texto
   legible explicando por qué se llegó a esa predicción.

Usa solo cálculos matemáticos (numpy) y NO requiere ninguna API de pago.
Puede opcionalmente usar un modelo de lenguaje gratuito para enriquecer
la explicación, pero es completamente funcional sin él.
"""

import math
from collections import Counter

import numpy as np

# ---------------------------------------------------------------------------
# Utilidades matemáticas
# ---------------------------------------------------------------------------


def poisson_pmf(lam, k):
    """
    Probabilidad de que una variable Pois(lam) sea exactamente k.
    Distribución de Poisson: P(X=k) = (lambda^k * e^-lambda) / k!
    """
    return (lam**k) * math.exp(-lam) / math.factorial(k)


def match_probabilities(lam_home, lam_away, max_goals=8):
    """
    Calcula la distribución de resultados usando Poisson bivariada.
    Devuelve (P(home win), P(draw), P(away win)) y las tablas de
    probabilidades de goles (para over/under y btts).

    lam_home: goles esperados del equipo local
    lam_away: goles esperados del equipo visitante
    """
    probs = np.zeros((max_goals + 1, max_goals + 1))

    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            probs[i, j] = poisson_pmf(lam_home, i) * poisson_pmf(lam_away, j)

    # Normalizamos para que sume ~1 (por el truncamiento)
    probs /= probs.sum()

    home_win = 0.0
    draw = 0.0
    away_win = 0.0
    total_gt_1 = 0.0  # P(total > 1) -> no lo usamos directamente
    total_gt_2 = 0.0  # P(total > 2) -> over 2.5 = total >= 3
    btts = 0.0  # ambos marcan (home>=1 AND away>=1)

    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            p = probs[i, j]
            if i > j:
                home_win += p
            elif i == j:
                draw += p
            else:
                away_win += p
            if i + j > 2:
                total_gt_2 += p
            if i >= 1 and j >= 1:
                btts += p

    # Compensamos cualquier residuo de normalización
    home_win += draw / (home_win + draw + away_win) * 0

    # Over 2.5 = total >= 3 goles
    over25 = total_gt_2
    under25 = 1.0 - over25

    return {
        "home": home_win,
        "draw": draw,
        "away": away_win,
        "over25": over25,
        "under25": under25,
        "btts_yes": btts,
        "btts_no": 1.0 - btts,
        "prob_matrix": probs,
        "lam_home": lam_home,
        "lam_away": lam_away,
    }


# ---------------------------------------------------------------------------
# Cálculo de los goles esperados (lambda) a partir de los datos
# ---------------------------------------------------------------------------


def expected_goals(team_data, opponent_data, is_home, h2h=None):
    """
    Estima los goles esperados (lambda) de un equipo en un partido.

    Método:
      - Partimos de los goles a favor/partido del equipo (ataque).
      - Ajustamos por los goles en contra/partido del rival (defensa).
      - Aplicamos ventaja de localía (+0.3 goles si juega en casa).

    Es un modelo simple y didáctico, no pretende ser perfecto.
    """
    # Goles a favor del equipo (ataque) por partido
    if team_data["goals_for"] > 0:
        attack = team_data["goals_for"] / 25.0
    else:
        attack = 1.3  # valor por defecto

    # Goles en contra del rival (defensa) por partido
    if opponent_data["goals_against"] > 0:
        defense = opponent_data["goals_against"] / 25.0
    else:
        defense = 1.3

    # El equipo puede marcar más si ataca bien y el rival defendla mal.
    # Combinamos ataque y defensa, ponderando la media geométrica.
    raw = math.sqrt(attack * defense) * 1.05

    # Bonus por localía (si el equipo es el local)
    if is_home:
        raw += 0.35
    else:
        raw -= 0.20

    # Ajuste por forma reciente (si el equipo viene de ganar, sube un poco)
    form = team_data.get("recent", "DDDDD")
    form_bonus = 0.0
    for r in form:
        if r == "W":
            form_bonus += 0.06
        elif r == "L":
            form_bonus -= 0.06
    raw += form_bonus / max(len(form), 1)

    # Limitamos el valor para que sea razonable (0.3 - 3.5 goles)
    raw = max(0.3, min(3.5, raw))

    return round(raw, 3)


def get_form_indicators(recent_form):
    """
    Calcula indicadores de forma a partir de la cadena W/D/L.
    Devuelve (wins, draws, losses, points, form_value).
    """
    if not recent_form:
        return 0, 0, 0, 0, 0
    counts = Counter(recent_form)
    wins = counts.get("W", 0)
    draws = counts.get("D", 0)
    losses = counts.get("L", 0)
    total = len(recent_form)
    points = wins * 3 + draws  # puntos según sistema 3-1-0
    # forma normalizada entre -1 y 1
    form_value = (wins - losses) / total
    return wins, draws, losses, points, form_value


# ---------------------------------------------------------------------------
# Explicación del razonamiento (genera texto claro)
# ---------------------------------------------------------------------------


def explain_reasoning(
    team_home,
    team_away,
    data_home,
    data_away,
    result,
    over25,
    btts,
    probs,
    h2h_info=None,
):
    """
    Genera una explicación en lenguaje natural (español) del porqué
    de la predicción. Es puramente basado en reglas/estadística y
    no requiere LLM ni API de pago.
    """
    lines = []

    # --- Forma reciente de ambos equipos ---
    w_h, d_h, l_h, pts_h, form_val_h = get_form_indicators(data_home.get("recent", ""))
    w_a, d_a, l_a, pts_a, form_val_a = get_form_indicators(data_away.get("recent", ""))

    lines.append("**1. Forma reciente (últimos partidos):**")
    lines.append(
        f"- **{team_home}**: {w_h}V {d_h}E {l_h}D ({data_home.get('recent', 'N/D')})"
    )
    lines.append(
        f"- **{team_away}**: {w_a}V {d_a}E {l_a}D ({data_away.get('recent', 'N/D')})"
    )

    if form_val_h > form_val_a:
        lines.append(
            f"- Habilidad: el equipo local llega en mejor forma (valor {form_val_h:.2f} vs {form_val_a:.2f})."
        )
    elif form_val_a > form_val_h:
        lines.append(
            f"- Habilidad: el visitante llega en mejor forma (valor {form_val_a:.2f} vs {form_val_h:.2f})."
        )
    else:
        lines.append("- Habilidad: ambos llegan con forma similar.")

    # --- Enfrentamientos directos (H2H) ---
    if h2h_info:
        lines.append("**2. Enfrentamientos directos (H2H):**")
        if len(h2h_info) == 0:
            lines.append("- No hay datos H2H disponibles entre ambos.")
        else:
            h2h_home_wins = 0
            h2h_draws = 0
            h2h_away_wins = 0
            for row in h2h_info:
                h, a, gh, ga = row[0], row[1], row[2], row[3]
                if gh > ga:
                    if h == team_home or h == data_home.get("name"):
                        h2h_home_wins += 1
                    else:
                        h2h_away_wins += 1
                elif gh == ga:
                    h2h_draws += 1
                else:
                    if a == team_away or a == data_away.get("name"):
                        h2h_away_wins += 1
                    else:
                        h2h_home_wins += 1
            lines.append(
                f"- Se han registrado {len(h2h_info)} enfrentamientos:"
                f" {h2h_home_wins} a favor de {team_home},"
                f" {h2h_draws} empates y {h2h_away_wins} a favor de {team_away}."
            )

    # --- Modelo estadístico ---
    lines.append("**3. Modelo estadístico (Poisson):**")
    lines.append(f"- Goles esperados: {team_home} {probs['lam_home']:.2f} -"
                 f" {probs['lam_away']:.2f} {team_away}.")
    lines.append(f"- Con esta estimación, el modelo asigna:")
    lines.append(f"  - 1 (Victoria local): {result.get('home', probs['home']):.1%}")
    lines.append(f"  - X (Empate):        {result.get('draw', probs['draw']):.1%}")
    lines.append(f"  - 2 (Victoria visita): {result.get('away', probs['away']):.1%}")

    # --- Mercados secundarios ---
    lines.append("**4. Mercados secundarios:**")
    if over25 > 0.5:
        lines.append(f"- Over 2.5: {over25:.1%} → se apuesta al **OVER**.")
    else:
        lines.append(f"- Over 2.5: {over25:.1%} → se apuesta al **UNDER**.")

    if probs["btts_yes"] > 0.5:
        lines.append(f"- Ambos marcan: {probs['btts_yes']:.1%} → se apuesta **SÍ**.")
    else:
        lines.append(f"- Ambos marcan: {probs['btts_yes']:.1%} → se apuesta **NO**.")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Función principal de predicción
# ---------------------------------------------------------------------------


def predict_match(team_home, team_away):
    """
    Predice el resultado de un partido dado dos nombre de equipos.
    Devuelve un diccionario completo con todos los datos de la predicción.

    NOTA: Esta función espera que ya tengas los datos (data_home, data_away).
    Para un uso directo usa predict_from_names().
    """
    # placeholder - se implementa en predict_from_names con datos ya cargados
    raise NotImplementedError(
        "Usa predict_from_names() o pasa los datos explícitamente."
    )


def predict_from_data(team_home, team_away, data_home, data_away, h2h=None, venue="home"):
    """
    Función principal que toma los datos de los dos equipos y calcula
    la predicción completa.

    Parámetros:
      team_home, team_away: nombres (str)
      data_home, data_away: diccionarios con 'goals_for', 'goals_against', 'recent'
      h2h: lista de enfrentamientos (opcional)
      venue: "home", "neutral", "away" - influye en la ventaja de localía

    Devuelve un diccionario con 'probabilities', 'prediction' y 'explanation'.
    """
    # Ajustamos la localía según el escenario
    is_home_team_home = venue == "home"

    # Calculamos goles esperados
    if venue == "home":
        lam_home = expected_goals(data_home, data_away, True, h2h)
        lam_away = expected_goals(data_away, data_home, False, h2h)
    elif venue == "away":
        # Invertimos: el equipo 'home' es en realidad visitante
        lam_home = expected_goals(data_home, data_away, False, h2h)
        lam_away = expected_goals(data_away, data_home, True, h2h)
    else:  # neutral
        lam_home = expected_goals(data_home, data_away, False, h2h)
        lam_away = expected_goals(data_away, data_home, False, h2h)

    probs = match_probabilities(lam_home, lam_away)

    # Decisión 1X2
    home_chance = probs["home"]
    draw_chance = probs["draw"]
    away_chance = probs["away"]

    if home_chance >= away_chance and home_chance >= draw_chance:
        prediction_1x2 = "1"
        porcentaje_principal = home_chance
    elif away_chance > home_chance and away_chance >= draw_chance:
        prediction_1x2 = "2"
        porcentaje_principal = away_chance
    else:
        prediction_1x2 = "X"
        porcentaje_principal = draw_chance

    # Over/under 2.5
    over25 = probs["over25"]
    if over25 >= 0.5:
        over_pred = "Over 2.5"
    else:
        over_pred = "Under 2.5"

    # Ambos marcan
    btts = probs["btts_yes"]
    if btts >= 0.5:
        btts_pred = "Sí (ambos marcan)"
    else:
        btts_pred = "No (no marcan ambos)"

    # Explicación
    explanation = explain_reasoning(
        team_home,
        team_away,
        data_home,
        data_away,
        {"home": home_chance, "draw": draw_chance, "away": away_chance},
        over25,
        btts,
        probs,
        h2h_info=h2h,
    )

    return {
        "prediction_1x2": prediction_1x2,
        "prob_1x2": {
            "home": home_chance,
            "draw": draw_chance,
            "away": away_chance,
        },
        "over_under": over_pred,
        "over25_prob": over25,
        "both_teams_score": btts_pred,
        "btts_prob": btts,
        "expected_goals": {"home": lam_home, "away": lam_away},
        "explanation": explanation,
        "prob_matrix": probs["prob_matrix"],
    }


def predict_from_names(team_home, team_away, data_fetcher=None):
    """
    Función de conveniencia: recibe nombres de equipos y usa el
    data_fetcher para obtener los datos automáticamente.
    Se usa sobre todo en la CLI e interfaz.

    data_fetcher: módulo con get_team_data() y get_h2h().
                  Si es None, no se enriquecen datos (requiere datos pasados).
    """
    if data_fetcher is None:
        raise ValueError("Debes pasar el módulo data_fetcher con datos.")

    data_home = data_fetcher.get_team_data(team_home)
    data_away = data_fetcher.get_team_data(team_away)
    h2h = data_fetcher.get_h2h(team_home, team_away)

    return predict_from_data(
        team_home, team_away, data_home, data_away, h2h=h2h, venue="home"
    )


if __name__ == "__main__":
    # Ejemplo rápido de uso: predicción del clásico
    import data_fetcher as df

    match = predict_from_names("Real Madrid", "Barcelona", df)
    print(f"Predicción 1X2: {match['prediction_1x2']}")
    print(f"Probabilidades: {match['prob_1x2']}")
    print(f"Over/Under: {match['over_under']} ({match['over25_prob']:.1%})")
    print(f"Ambos marcan: {match['both_teams_score']}")
    print("\nExplicación:\n", match["explanation"])
