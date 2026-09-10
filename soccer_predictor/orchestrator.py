"""
Orquestador principal del predictor de fútbol.

Este módulo une:
  - La obtención de datos (data_fetcher.py)
  - El motor estadístico de predicción (prediction_engine.py)

y expone una función única `predict(team_home, team_away, competition, date)`
que usa la interfaz (CLI o Streamlit).
"""

try:
    from . import data_fetcher as df
    from . import prediction_engine as pe
    from . import llm_reasoning as llm
except ImportError:
    import data_fetcher as df
    import prediction_engine as pe
    import llm_reasoning as llm


def predict(
    team_home,
    team_away,
    competition="",
    date="",
    venue="home",
    live=True,
    with_news=False,
    refresh=False,
    player_form=True,
    absences_home=0,
    absences_away=0,
):
    """
    Función principal de predicción.

    Parámetros:
      team_home  (str): nombre del equipo local (cualquiera, se busca en vivo)
      team_away  (str): nombre del equipo visitante (cualquiera)
      competition(str): nombre de la competición (solo informativo, para el texto)
      date       (str): fecha del partido (informativo)
      venue      (str): "home", "neutral" o "away"
      live       (bool): si True, busca datos recientes en internet
      with_news  (bool): si True, añade noticias (lesiones/forma) al contexto
      refresh    (bool): si True, ignora la caché JSON y re-descarga
      player_form(bool): si True, busca goleadores en racha (OpenLigaDB)
      absences_home/away (int): bajas importantes manuales (lesión/sanción)

    Todo lo descargado se guarda en data/db/*.json y el pronóstico
    se añade al log de predicciones.
    """
    # 1. Normalizamos los nombres (BBDD + semilla estática)
    team_home = df.parse_team_input(team_home)
    team_away = df.parse_team_input(team_away)

    # 2. Obtenemos datos de ambos equipos (live + caché JSON)
    data_home = df.get_team_data(team_home, live=live, with_news=with_news, refresh=refresh)
    data_away = df.get_team_data(team_away, live=live, with_news=with_news, refresh=refresh)

    # 3. Obtenemos historial H2H (caché + live + estático)
    h2h = df.get_h2h(team_home, team_away, live=live)

    # 3b. Racha de goleadores (mejor esfuerzo; None si no hay cobertura)
    ctx_home = ctx_away = None
    if player_form:
        try:
            try:
                from .scrapers import player_form as _pf
            except ImportError:
                from scrapers import player_form as _pf
            ctx_home = _pf.hot_scorers(data_home.get("name", team_home))
            ctx_away = _pf.hot_scorers(data_away.get("name", team_away))
        except Exception:
            ctx_home = ctx_away = None

    # 4. Calculamos la predicción
    result = pe.predict_from_data(
        team_home,
        team_away,
        data_home,
        data_away,
        h2h=h2h,
        venue=venue,
        player_context_home=ctx_home,
        player_context_away=ctx_away,
        absences_home=absences_home,
        absences_away=absences_away,
    )

    # 5. Añadimos metadatos informativos
    result["competition"] = competition or "Competición no especificada"
    result["date"] = date or "Fecha no especificada"
    result["teams"] = {"home": team_home, "away": team_away}
    result["data_sources"] = {
        "home": data_home.get("source", "?"),
        "away": data_away.get("source", "?"),
        "home_recent": data_home.get("recent", ""),
        "away_recent": data_away.get("recent", ""),
    }
    result["player_context"] = {"home": ctx_home, "away": ctx_away}
    result["absences"] = {"home": absences_home, "away": absences_away}

    # 6. Opcionalmente enriquecemos la explicación con un LLM gratuito.
    #    Si no está configurado o falla, se mantiene la explicación estadística.
    base_explanation = result["explanation"]
    enriched, source = llm.enrich_explanation(result, base_explanation)
    result["explanation"] = enriched
    result["explanation_source"] = source

    # 7. Guardamos el pronóstico en la BBDD JSON (log para el histórico)
    try:
        try:
            from . import database as _db
        except ImportError:
            import database as _db
        _db.log_prediction(result)
    except Exception:
        pass

    return result
