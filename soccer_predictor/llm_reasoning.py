"""
Integración opcional con modelos de lenguaje (LLM) gratuitos para
enriquecer la explicación de la predicción.

El predictor funciona 100% SIN esto (usa su propio motor de explicación
basado en reglas). Pero si quieres un razonamiento "más natural", puedes
activar un LLM gratuito configurando dos variables de entorno:

  OPENAI_API_KEY        -> tu clave (la del proveedor gratuito que uses)
  OPENAI_BASE_URL       -> URL del endpoint compatible con OpenAI

  OPENAI_MODEL          -> nombre del modelo (opcional, default abajo)

Ejemplo usando un endpoint local gratuito (Ollama):
  OPENAI_BASE_URL=http://localhost:11434/v1
  OPENAI_API_KEY=ollama
  OPENAI_MODEL=llama3

Ejemplo con un proveedor gratis tipo OpenRouter/Groq:
  OPENAI_BASE_URL=https://api.openai.com/v1
  OPENAI_API_KEY=tu_clave
  OPENAI_MODEL=gpt-4o-mini

Si no se configura nada, o si la llamada falla, se usa la explicación
estadística por defecto sin ningún problema.
"""

import os

import requests

# Modelo por defecto (puede cambiarse con OPENAI_MODEL)
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def _is_configured():
    """Devuelve True si el usuario ha configurado un endpoint de LLM."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    base_url = os.getenv("OPENAI_BASE_URL", "").strip()
    # Si no hay api key ni base_url, no está configurado.
    # Si hay base_url pero no key, asumimos que el endpoint lo permite
    # (ej. un modelo local tipo Ollama que no exige key).
    return bool(base_url or api_key)


def enrich_explanation(prediction_data, fallback_explanation):
    """
    Intenta generar una explicación mejorada usando un LLM gratuito.

    Recibe:
      prediction_data: diccionario con los datos numéricos de la predicción
      fallback_explanation: la explicación estándar (por si falla el LLM)

    Devuelve:
      (texto_explicación, fuente) donde fuente es "llm" o "estadistica"
    """
    if not _is_configured():
        return fallback_explanation, "estadistica"

    try:
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        model = os.getenv("OPENAI_MODEL", DEFAULT_MODEL)

        # Construimos el prompt con los datos de la predicción
        home = prediction_data["teams"]["home"]
        away = prediction_data["teams"]["away"]
        p = prediction_data["prob_1x2"]

        prompt = (
            f"Analiza el siguiente partido de fútbol y da una explicación "
            f"clara y concisa (en español) de por qué se prevé este resultado.\n\n"
            f"Partido: {home} vs {away}\n"
            f"Competición: {prediction_data.get('competition', 'N/D')}\n"
            f"Fecha: {prediction_data.get('date', 'N/D')}\n\n"
            f"Probabilidades estimadas por modelo estadístico:\n"
            f"- 1 ({home}): {p['home']*100:.1f}%\n"
            f"- X (Empate): {p['draw']*100:.1f}%\n"
            f"- 2 ({away}): {p['away']*100:.1f}%\n"
            f"Pronóstico: {prediction_data['prediction_1x2']}\n"
            f"Over/Under 2.5: {prediction_data['over_under']}\n"
            f"Ambos marcan: {prediction_data['both_teams_score']}\n\n"
            f"Explica de forma breve (5-7 líneas) qué factores podrían "
            f"respaldar o matizar esta predicción."
        )

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Eres un analista de fútbol objetivo. Tus análisis "
                        "son probabilísticos, no certezas."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.6,
            "max_tokens": 400,
        }

        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        resp = requests.post(
            f"{base_url}/chat/completions",
            json=payload,
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()

        content = resp.json()["choices"][0]["message"]["content"].strip()
        if not content:
            return fallback_explanation, "estadistica"

        return content, "llm"
    except Exception:
        # Cualquier fallo (sin internet, endpoint caído, etc.) -> fallback
        return fallback_explanation, "estadistica"
