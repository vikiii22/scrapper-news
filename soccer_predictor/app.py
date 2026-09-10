"""
Interfaz web (Streamlit) para el predictor de fútbol.

Uso:
    streamlit run url_app.py

o simplemente:

    cd soccer_predictor
    streamlit run app.py
"""

import sys

import streamlit as st

# Importamos los módulos del paquete (ajustamos el path si hace falta)
try:
    from .orchestrator import predict
    from . import data_fetcher as df
    from . import quiniela as qui
    from . import database as db
except ImportError:
    sys.path.insert(0, ".")  # añadimos el directorio actual
    from orchestrator import predict
    import data_fetcher as df
    import quiniela as qui
    import database as db


# ---------------------------------------------------------------------------
# Configuración de la página
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="⚽ Predictor de Fútbol",
    page_icon="⚽",
    layout="centered",
)

st.title("⚽ Predictor de Fútbol (gratuito)")
st.markdown(
    "Predice el resultado 1X2, Over/Under 2.5 y Ambos Marcan "
    "usando un modelo estadístico sin coste."
)

seccion = st.sidebar.radio("Sección", ["🔮 Partido", "🎫 Quiniela"])

if seccion == "🎫 Quiniela":
    st.header("🎫 Quiniela (boleto LAE)")
    st.markdown(
        "Pega el HTML del boleto (jornada con % LAE), se extraen los "
        "partidos, se calculan los pronósticos con datos en vivo y se "
        "guardan en `data/db/quiniela.json`."
    )

    html_in = st.text_area("HTML del boleto", height=180,
                           placeholder="Pega aquí el HTML copiado de la página de LAE...")
    col_q1, col_q2, col_q3 = st.columns(3)
    comp_q = col_q1.selectbox("Competición por defecto", df.get_competitions())
    live_q = col_q2.checkbox("Datos en vivo", value=True)
    refresh_q = col_q3.checkbox("Forzar recarga", value=False)

    if st.button("1️⃣ Leer boleto") and html_in.strip():
        parsed = qui.parse_quiniela_html(html_in)
        st.session_state["quiniela_parsed"] = parsed
        if not parsed["matches"]:
            st.error("No se reconoció ningún partido en ese HTML.")
        else:
            st.success(f"Jornada {parsed['jornada']} · {len(parsed['matches'])} partidos detectados.")

    parsed = st.session_state.get("quiniela_parsed")
    if parsed and parsed["matches"]:
        st.subheader(f"Boleto · Jornada {parsed['jornada']}")
        st.dataframe(
            [{
                "Nº": m["n"],
                "Partido": f"{m['home']} - {m['away']}",
                "Día": f"{m['day']} {m['hour']}".strip(),
                "LAE 1/X/2": ("—" if not m["lae"] else
                    f"{m['lae']['1']:.0f}/{m['lae']['X']:.0f}/{m['lae']['2']:.0f}"),
                "Pleno": "sí" if m["is_pleno"] else "",
                "Fem.": "sí" if m["is_women"] else "",
            } for m in parsed["matches"]],
            use_container_width=True,
        )

        if st.button("2️⃣ Calcular pronósticos y guardar en BBDD"):
            bar = st.progress(0, text="Analizando partidos...")
            analysis = qui.analyze_quiniela(
                parsed, competition_default=comp_q, live=live_q, refresh=refresh_q,
                progress_cb=lambda i, t: bar.progress(i / t, text=f"Partido {i}/{t}"),
            )
            entry = db.save_quiniela(parsed["jornada"], analysis)
            st.session_state["quiniela_analysis"] = entry
            bar.empty()

        analysis = st.session_state.get("quiniela_analysis")
        if analysis:
            st.subheader(f"Pronósticos · Jornada {analysis['jornada']}")
            rows = []
            for m in analysis["matches"]:
                if "error" in m:
                    rows.append({"Nº": m["n"],
                                 "Partido": f"{m['home']} - {m['away']}",
                                 "Resultado": f"⚠️ {m['error']}"})
                    continue
                val = m.get("valor") or {}
                rows.append({
                    "Nº": m["n"],
                    "Partido": f"{m['home']} - {m['away']}",
                    "Modelo 1/X/2": (f"{m['modelo']['1']:.0f}/{m['modelo']['X']:.0f}/{m['modelo']['2']:.0f}"),
                    "Pick": m["pick"] + (f" (pleno {m['pleno_sugerido']['home']}-{m['pleno_sugerido']['away']})"
                                         if m.get("pleno_sugerido") else ""),
                    "Valor vs LAE": (f"{val.get('1', 0):+.0f}/{val.get('X', 0):+.0f}/{val.get('2', 0):+.0f}"
                                     if val else "—"),
                    "Apuesta valor": m.get("value_pick") or "—",
                })
            st.dataframe(rows, use_container_width=True)
            st.success(f"Guardado en BBDD de quiniela (jornada {analysis['jornada']}).")

    st.divider()
    st.subheader("🗄️ Jornadas guardadas")
    saved = db.list_quinielas()
    if saved:
        sel = st.selectbox("Ver jornada", saved)
        q = db.get_quiniela(sel)
        if q:
            st.write(f"Analizada: {q['analyzed_at'][:16].replace('T', ' ')} · "
                     f"{len(q['matches'])} partidos")
            for m in q["matches"]:
                extra = "" if "error" in m else f" → modelo {m['pick']} · valor {m.get('value_pick') or '—'}"
                st.write(f"**{m['n']}.** {m['home']} - {m['away']}{extra}")
    else:
        st.caption("Aún no hay jornadas guardadas.")

    st.stop()


# ---------------------------------------------------------------------------
# Formulario de entrada
# ---------------------------------------------------------------------------
with st.form("prediction_form"):
    col1, col2 = st.columns(2)

    available = df.get_available_teams()

    with col1:
        team_home = st.text_input(
            "Equipo local (casa)",
            placeholder="Ej: Levante, Real Madrid...",
        )
    with col2:
        team_away = st.text_input(
            "Equipo visitante",
            placeholder="Ej: Levante, Barcelona...",
        )

    st.caption(
        "Escribe el nombre de cualquier equipo. Sugerencias: "
        + ", ".join(available)
    )

    competition = st.selectbox(
        "Competición",
        df.get_competitions(),
    )

    date = st.date_input("Fecha del partido")

    venue = st.radio(
        "Sede del partido",
        ["home", "neutral", "away"],
        index=0,
        format_func=lambda v: {
            "home": "En casa (local)",
            "neutral": "Campo neutral",
            "away": "Fuera de casa",
        }[v],
    )

    col_live, col_ref, col_news = st.columns(3)
    live = col_live.checkbox("Datos en vivo", value=True,
        help="Busca forma reciente en internet para CUALQUIER equipo y lo guarda en la BBDD JSON.")
    refresh = col_ref.checkbox("Forzar recarga", value=False,
        help="Ignora la caché local y vuelve a descargar.")
    with_news = col_news.checkbox("Con noticias", value=False,
        help="Añade noticias de lesiones/forma (más lento).")

    col_b1, col_b2 = st.columns(2)
    bajas_home = col_b1.number_input("Bajas importantes local", min_value=0, max_value=11, value=0,
        help="Titulares lesionados/sancionados del local. Resta ~0.08 goles esperados por baja.")
    bajas_away = col_b2.number_input("Bajas importantes visitante", min_value=0, max_value=11, value=0,
        help="Titulares lesionados/sancionados del visitante.")

    submit = st.form_submit_button("🔮 Predecir partido")


# ---------------------------------------------------------------------------
# Cálculo y visualización de resultados cuando se envía el formulario
# ---------------------------------------------------------------------------
if submit:
    if not team_home.strip() or not team_away.strip():
        st.error("Introduce el nombre de ambos equipos (local y visitante).")
    elif team_home.strip().lower() == team_away.strip().lower():
        st.error("El equipo local y el visitante no pueden ser el mismo.")
    else:
        with st.spinner("Calculando predicción..."):
            result = predict(team_home, team_away, competition, str(date), venue,
                            live=live, with_news=with_news, refresh=refresh,
                            absences_home=int(bajas_home), absences_away=int(bajas_away))

        st.subheader(f"{team_home} vs {team_away}")
        st.caption(f"{competition} · {date}")

        # --- Indicador principal 1X2 ---
        pred_1x2 = {
            "1": team_home,
            "X": "Empate",
            "2": team_away,
        }
        st.markdown(
            f"### 🎯 Pronóstico: **{pred_1x2[result['prediction_1x2']]}**"
        )

        # --- Probabilidades 1X2 ---
        p = result["prob_1x2"]
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("1 · " + team_home, f"{p['home']:.1%}")
        col_b.metric("X · Empate", f"{p['draw']:.1%}")
        col_c.metric("2 · " + team_away, f"{p['away']:.1%}")

        st.divider()

        # --- Mercados secundarios ---
        col_d, col_e, col_f = st.columns(3)
        col_d.metric("Over/Under 2.5", result["over_under"])
        col_e.metric("Ambos marcan", result["both_teams_score"])
        col_f.metric(
            "Goles esperados",
            f"{result['expected_goals']['home']:.2f} - "
            f"{result['expected_goals']['away']:.2f}",
        )

        st.divider()

        # --- Razonamiento ---
        st.markdown("### 📝 Razonamiento")
        st.markdown(result["explanation"])
        src = result.get("explanation_source", "estadistica")
        st.caption(f"Fuente del razonamiento: {'LLM gratuito' if src == 'llm' else 'modelo estadístico'}")
        ds = result.get("data_sources", {})
        if ds:
            st.caption(f"Datos: local {ds.get('home')} [{ds.get('home_recent')}] · "
                       f"visitante {ds.get('away')} [{ds.get('away_recent')}] · "
                       f"guardado en data/db/*.json")
        pc = result.get("player_context", {}) or {}
        with st.expander("⚽ Racha de goleadores (OpenLigaDB)"):
            for side, label in (("home", team_home), ("away", team_away)):
                ctx = pc.get(side) or {}
                sc = ctx.get("scorers") or []
                if sc:
                    st.write(f"**{label}**: " + ", ".join(
                        f"{s['name']} ({s['goals']}g en últimos {ctx.get('matches_analyzed', '?')})" for s in sc))
                else:
                    st.write(f"**{label}**: sin cobertura de goleadores.")
            pa = result.get("player_adjustments", {}) or {}
            st.caption(f"Ajuste aplicado: local {pa.get('home', 0):+.2f} / visitante {pa.get('away', 0):+.2f} goles esperados.")

        st.info("ℹ️ Modelo estadístico de Poisson. No es una garantía de resultado.")

with st.expander("🗄️ Estado de la BBDD local (JSON)"):
    try:
        try:
            from . import database as _db
        except ImportError:
            import database as _db
        s = _db.stats()
        st.write(f"Carpeta: `{s['db_dir']}`")
        c1, c2, c3 = st.columns(3)
        c1.metric("Equipos", s["teams"])
        c2.metric("Parejas H2H", s["h2h_pairs"])
        c3.metric("Pronósticos", s["predictions"])
    except Exception as e:
        st.warning(f"No se pudo leer la BBDD: {e}")
