"""
Chat simple para hablar con un modelo local de Ollama.

Interfaz minima: historial, streaming token a token, selector de modelo y
prompt de sistema editable. No necesita internet ni claves de API.

Uso:
    pip install -r deploy/ia/requirements.txt
    streamlit run deploy/ia/chat.py

Requiere Ollama escuchando en OLLAMA_URL (por defecto http://localhost:11434):
  - Docker:  docker compose -f deploy/ia/docker-compose.yml up -d
  - Nativo:  ollama serve
"""

import json
import os

import requests
import streamlit as st

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:4b")
SYSTEM_DEFAULT = "Eres un asistente util. Responde en espanol, claro y breve."


# --------------------------------------------------------------------------- #
# Comunicacion con Ollama
# --------------------------------------------------------------------------- #
def listar_modelos(url):
    """Devuelve los modelos descargados, o [] si Ollama no responde."""
    try:
        r = requests.get(f"{url}/api/tags", timeout=3)
        r.raise_for_status()
        return sorted(m["name"] for m in r.json().get("models", []))
    except requests.RequestException:
        return []


def stream_respuesta(url, modelo, mensajes, temperatura):
    """Genera la respuesta del modelo trozo a trozo (streaming)."""
    payload = {
        "model": modelo,
        "messages": mensajes,
        "stream": True,
        "options": {"temperature": temperatura},
    }
    with requests.post(f"{url}/api/chat", json=payload, stream=True, timeout=600) as r:
        r.raise_for_status()
        for linea in r.iter_lines():
            if not linea:
                continue
            evento = json.loads(linea)
            if evento.get("error"):
                raise RuntimeError(evento["error"])
            contenido = evento.get("message", {}).get("content")
            if contenido:
                yield contenido
            if evento.get("done"):
                break


# --------------------------------------------------------------------------- #
# Estado de la sesion
# --------------------------------------------------------------------------- #
st.set_page_config(page_title="Chat local", page_icon="💬", layout="centered")

if "mensajes" not in st.session_state:
    st.session_state.mensajes = []

# --------------------------------------------------------------------------- #
# Barra lateral: conexion y ajustes
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.subheader("⚙️ Ajustes")

    url = st.text_input("Servidor Ollama", value=OLLAMA_URL).rstrip("/")

    modelos = listar_modelos(url)
    if modelos:
        indice = modelos.index(DEFAULT_MODEL) if DEFAULT_MODEL in modelos else 0
        modelo = st.selectbox("Modelo", modelos, index=indice)
        st.caption(f"{len(modelos)} modelo(s) disponible(s)")
    else:
        modelo = DEFAULT_MODEL
        st.error("No hay conexion o no hay modelos descargados.")
        st.code(f"ollama pull {DEFAULT_MODEL}", language="powershell")

    if st.button("🔄 Recargar modelos"):
        st.rerun()

    temperatura = st.slider("Creatividad", 0.0, 1.5, 0.7, 0.1)

    sistema = st.text_area("Instrucciones del asistente", SYSTEM_DEFAULT, height=120)

    st.divider()
    if st.button("🗑️ Borrar conversacion"):
        st.session_state.mensajes = []
        st.rerun()

# --------------------------------------------------------------------------- #
# Conversacion
# --------------------------------------------------------------------------- #
st.title("💬 Chat local")
st.caption(f"{modelo} · {url} · sin conexion a internet")

if not st.session_state.mensajes:
    st.info(
        "Escribe abajo para empezar. Todo se ejecuta en tu equipo: "
        "nada sale de aqui."
    )

for mensaje in st.session_state.mensajes:
    with st.chat_message(mensaje["role"]):
        st.markdown(mensaje["content"])

if pregunta := st.chat_input("Escribe tu mensaje..."):
    st.session_state.mensajes.append({"role": "user", "content": pregunta})
    with st.chat_message("user"):
        st.markdown(pregunta)

    # El prompt de sistema va primero pero no se guarda en el historial visible.
    contexto = [{"role": "system", "content": sistema}] if sistema.strip() else []
    contexto += st.session_state.mensajes

    with st.chat_message("assistant"):
        try:
            respuesta = st.write_stream(
                stream_respuesta(url, modelo, contexto, temperatura)
            )
            st.session_state.mensajes.append(
                {"role": "assistant", "content": respuesta}
            )
        except requests.ConnectionError:
            st.error(
                f"No puedo conectar con Ollama en `{url}`.\n\n"
                "Arrancalo con `docker compose -f deploy/ia/docker-compose.yml up -d` "
                "o con `ollama serve` si lo tienes instalado en Windows."
            )
        except requests.HTTPError as e:
            st.error(f"Ollama devolvio un error: {e.response.status_code} {e}")
        except Exception as e:  # noqa: BLE001 - nunca romper la interfaz
            st.error(f"Error inesperado: {e}")
