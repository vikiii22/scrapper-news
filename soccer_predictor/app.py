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
                pp = m.get("positions") or {}
                ph, pa = pp.get("home") or {}, pp.get("away") or {}
                rows.append({
                    "Nº": m["n"],
                    "Partido": f"{m['home']} - {m['away']}",
                    "Pos.": (f"{ph.get('pos', '—')}º vs {pa.get('pos', '—')}º"
                             if (ph or pa) else "—"),
                    "Modelo 1/X/2": (f"{m['modelo']['1']:.0f}/{m['modelo']['X']:.0f}/{m['modelo']['2']:.0f}"),
                    "Pick": m["pick"] + (f" (pleno {m['pleno_sugerido']['home']}-{m['pleno_sugerido']['away']})"
                                         if m.get("pleno_sugerido") else "") + (" ⚠️" if m.get("low_confidence") else ""),
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

            # --- Resultados reales y acierto ---
            st.subheader(f"✅ Resultados reales · Jornada {sel}")
            actuals = {int(k): v for k, v in (q.get("actuals") or {}).items()}

            if st.button("⬇️ Descargar resultados (ESPN)"):
                bar = st.progress(0, text="Buscando resultados...")
                found = qui.fetch_actuals(
                    q["matches"],
                    progress_cb=lambda i, t: bar.progress(i / t, text=f"Partido {i}/{t}"))
                bar.empty()
                actuals.update(found)
                st.session_state["quiniela_actuals"] = actuals
                st.success(f"Encontrados {len(found)} de {len(q['matches'])} "
                           f"(el resto mételo a mano).")

            actuals = st.session_state.get("quiniela_actuals", actuals)
            st.caption("Corrige o completa a mano: elige el signo real de cada partido.")
            edited = {}
            for m in q["matches"]:
                if "error" in m:
                    continue
                cur = (actuals.get(m["n"]) or {}).get("sign", "—")
                opts = ["—", "1", "X", "2"]
                pick = st.selectbox(
                    f"{m['n']}. {m['home']} - {m['away']}"
                    + (f" (auto: {(actuals.get(m['n']) or {}).get('score', '')} "
                       f"{(actuals.get(m['n']) or {}).get('sign', '')})" if m["n"] in actuals else ""),
                    opts, index=opts.index(cur) if cur in opts else 0,
                    key=f"real_{sel}_{m['n']}")
                if pick != "—":
                    prev = actuals.get(m["n"], {})
                    edited[m["n"]] = {"sign": pick,
                                      "home_goals": prev.get("home_goals", 0),
                                      "away_goals": prev.get("away_goals", 0),
                                      "score": prev.get("score", ""),
                                      "source": prev.get("source", "manual")}
            pleno_m = next((x for x in q["matches"] if x.get("is_pleno")), None)
            if pleno_m and pleno_m["n"] in edited:
                st.caption("Para el pleno valen los goles: si el auto no los trajo, "
                           "cuenta como fallo de pleno pero el 1X2 sí puntúa.")
                cgh, cga = st.columns(2)
                gh = cgh.number_input("Goles local (pleno)", 0, 9,
                                      value=int((actuals.get(pleno_m["n"]) or {}).get("home_goals", 0) or 0),
                                      key=f"pg_h_{sel}")
                ga = cga.number_input("Goles visitante (pleno)", 0, 9,
                                      value=int((actuals.get(pleno_m["n"]) or {}).get("away_goals", 0) or 0),
                                      key=f"pg_a_{sel}")
                edited[pleno_m["n"]].update(home_goals=int(gh), away_goals=int(ga),
                                            score=f"{int(gh)}-{int(ga)}")

            if st.button("💾 Guardar resultados y calcular acierto"):
                score = qui.score_analysis(q["matches"], edited)
                db.save_quiniela_results(sel, edited, score)
                st.session_state["quiniela_actuals"] = edited
                st.success("Resultados guardados.")

            # --- Boleto realmente jugado (puede diferir del modelo) ---
            st.subheader("🎫 Lo que marcaste en tu boleto")
            st.caption("Si jugaste otro signo distinto al del modelo, márcalo: "
                       "así medimos al modelo Y a tus decisiones por separado.")
            q = db.get_quiniela(sel)
            played_prev = {int(k): v for k, v in (q.get("played") or {}).items()}
            played_new = {}
            for m in q["matches"]:
                if "error" in m:
                    continue
                cur = played_prev.get(m["n"], m.get("pick", "1"))
                played_new[m["n"]] = st.selectbox(
                    f"{m['n']}. {m['home']} - {m['away']} (modelo: {m.get('pick', '?')})",
                    ["1", "X", "2"],
                    index=["1", "X", "2"].index(cur) if cur in ("1", "X", "2") else 0,
                    key=f"played_{sel}_{m['n']}")
            if st.button("💾 Guardar boleto jugado"):
                db.save_played(sel, played_new)
                q2 = db.get_quiniela(sel)
                sc = qui.score_analysis(q2["matches"], q2.get("actuals", {}), played_new)
                db.save_quiniela_results(sel, q2.get("actuals", {}), sc)
                st.success("Boleto guardado y acierto recalculado.")

            q = db.get_quiniela(sel)  # recargar por si se guardó
            if q.get("score"):
                s = q["score"]
                c1, c2, c3, c4 = st.columns(4)
                p, v = s["pick"], s["value"]
                c1.metric("Acierto 1X2", f"{p['ok']}/{p['n']}",
                          f"{p['ok']/p['n']:.0%}" if p["n"] else None)
                c2.metric("Apuestas valor", f"{v['ok']}/{v['n']}",
                          f"{v['ok']/v['n']:.0%}" if v["n"] else None)
                pl = s.get("played", {})
                c3.metric("Tu boleto", f"{pl.get('ok', 0)}/{pl.get('n', 0)}",
                          f"{pl['ok']/pl['n']:.0%}" if pl.get("n") else None)
                c4.metric("Pleno", "✅" if s["pleno"]["ok"] else "❌")
                vers = q.get("versions", [])
                if vers:
                    st.caption("Versiones de análisis: " + " · ".join(
                        f"v{i+1} ({w.get('engine', '?')}, {w.get('analyzed_at', '')[:16].replace('T', ' ')})"
                        for i, w in enumerate(vers)))
                st.dataframe(
                    [{
                        "Nº": r["n"],
                        "Partido": f"{r['home']} - {r['away']}",
                        "Pick": r.get("pick", "—"),
                        "Jugada": (r.get("played", "—") +
                                   (" ✅" if r.get("played_ok") else (" ❌" if "played_ok" in r else ""))),
                        "Real": f"{r.get('actual', '—')} {r.get('score', '') or ''}".strip(),
                        "1X2": ("✅" if r.get("pick_ok") else "❌") if "pick_ok" in r else "—",
                        "Valor": (r.get("value_pick") or "—") +
                                 (" ✅" if r.get("value_ok") else (" ❌" if "value_ok" in r else "")),
                        "Pleno": (f"{r.get('pleno_sug', '')} vs {r.get('pleno_real', '')} "
                                  f"({'✅' if r.get('pleno_ok') else '❌'})") if "pleno_ok" in r else "—",
                    } for r in s["rows"]],
                    use_container_width=True,
                )
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

    women = st.checkbox("Partido femenino (Liga F)",
        help="Usa solo datos femeninos; nunca mezcla con masculinos.")

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
                            absences_home=int(bajas_home), absences_away=int(bajas_away),
                            women=women)

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
        pos = result.get("positions", {}) or {}
        ph, pa = pos.get("home") or {}, pos.get("away") or {}
        if ph or pa:
            tx_h = "%sº (%s pts en %sj)" % (ph["pos"], ph["pts"], ph["played"]) if ph else "—"
            tx_a = "%sº (%s pts en %sj)" % (pa["pos"], pa["pts"], pa["played"]) if pa else "—"
            st.caption("Clasificación: %s %s · %s %s" % (team_home, tx_h, team_away, tx_a))
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
        if result.get("low_confidence"):
            ni = result.get("normalization") or {}
            st.warning("⚠️ Cruce interligas (%s vs %s): las goleadas a rivales flojos "
                       "no son comparables. Confianza menor."
                       % (ni.get("home_league", "?"), ni.get("away_league", "?")))

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
