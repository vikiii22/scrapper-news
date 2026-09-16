# ⚽ Predictor de Fútbol (Gratuito)

Predictor de fútbol **100% gratuito** que estima el resultado 1X2,
el Over/Under 2.5 y si ambos equipos marcan, usando:

- Un **modelo estadístico de Poisson** (sin coste, sin API).
- Opcionalmente, **datos reales** desde fuentes gratuitas si configuras
  una API key (opcional, no es necesario para funcionar).
- Datos estáticos de ejemplo integrados para que funcione nada más abrirlo.

---

## ✅ Características

| Entrada            | Salida                                  |
|--------------------|-----------------------------------------|
| Equipo local       | Pronóstico 1X2 con probabilidades       |
| Equipo visitante   | Over / Under 2.5                        |
| Competición        | Ambos marcan (Sí/No)                    |
| Fecha              | Goles esperados                         |
| Sede               | Explicación del razonamiento (en español)|

---

## 📦 Instalación

Requisitos: **Python 3.9+**

```bash
# 1. Clona o descarga el proyecto y entra en la carpeta
cd soccer_predictor

# 2. (Recomendado) Crea un entorno virtual
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 3. Instala las dependencias
pip install -r requirements.txt
```

---

## 🚀 Cómo usar

### Opción A: Interfaz web (Streamlit) — la más fácil

```bash
cd soccer_predictor
streamlit run app.py
```

Se abrirá el navegador. Elige los equipos, la competición y pulsa
**"🔮 Predecir partido"**. ¡Listo!

### Opción B: Línea de comandos (CLI)

```bash
# Modo directo
python -m soccer_predictor.cli "Real Madrid" "Barcelona" -c "La Liga" -d "2026-09-15"

# Modo interactivo (te pide los datos paso a paso)
python -m soccer_predictor.cli
```

### Opción C: Desde Python (programáticamente)

```python
from soccer_predictor.orchestrator import predict

result = predict("Real Madrid", "Barcelona", "La Liga", "2026-09-15")
print(result["prediction_1x2"])   # '1', 'X' o '2'
print(result["explanation"])      # razonamiento en texto
```

---

## 🔌 Fuentes de datos gratuitas (opcional)

El predictor funciona **sin configurar nada** gracias a los datos estáticos
de ejemplo. Pero si quieres datos más reales, puedes activar una API gratuita:

### API-Football (recomendada, tier free)

1. Regístrate en [api-sports.io](https://www.api-football.com/) (plan free).
2. Crea un archivo `.env` en la carpeta del proyecto:

```
API_FOOTBALL_KEY=tu_clave_gratuita
```

3. Si la clave es válida, el predictor usará datos reales de forma/resultados.
   Si falla o no hay clave, usa automáticamente los datos estáticos.

### Football-Data.org (alternativa free)

```
FOOTBALL_DATA_TOKEN=tu_token_gratuito
```

> ⚠️ **Importante**: las API gratuitas tienen límites estrictos
> (ej. API-Football free: 100 peticiones/día). El predictor está diseñado
> para funcionar perfectamente sin ellas.

### 🧠 Razonamiento con LLM gratuito (opcional)

El predictor genera explicaciones claras **sin ningún LLM** (puro estadístico).
Pero si quieres un razonamiento con lenguaje más natural, puedes conectar un
modelo gratuito compatible con la API de OpenAI configurando en `.env`:

```
OPENAI_BASE_URL=https://api.openai.com/v1   # o el endpoint de tu proveedor gratis
OPENAI_API_KEY=tu_clave_gratuita
OPENAI_MODEL=gpt-4o-mini
```

Funciona con cualquier endpoint compatible (OpenRouter, Groq, Ollama local,
etc.). Si no se configura o falla la conexión, se usa automáticamente la
explicación estadística por defecto. **Nunca rompe la app.**

---

## 📁 Estructura del proyecto

```
soccer_predictor/
├── app.py                    # Interfaz web Streamlit
├── cli.py                    # Interfaz de línea de comandos
├── orchestrator.py           # Función principal predict()
├── data_fetcher.py           # Obtención de datos (API + estático + scraping)
├── prediction_engine.py      # Motor estadístico de Poisson + explicación
├── llm_reasoning.py          # Razonamiento LLM gratuito (opcional)
├── __init__.py
├── requirements.txt
└── README.md
```

---

## 🧠 Cómo funciona la predicción

1. **Obtención de datos**: se busca la forma reciente de cada equipo,
   su historial H2H y su posición (de API gratuita o datos estáticos).

2. **Motor estadístico**: se estima el número esperado de goles (λ) de cada
   equipo combinando ataque, defensa y ventaja de localía. Luego se usa la
   **distribución de Poisson** para calcular las probabilidades de cada
   resultado (1, X, 2), de los goles totales (over/under 2.5) y de que
   ambos marquen.

3. **Explicación**: se genera un texto claro en español explicando qué
   datos se usaron y por qué se llegó al pronóstico. No requiere ninguna
   API de pago.

---

## ⚠️ Aviso

Esto es una **herramienta educativa/estadística**. Las predicciones son
**probabilidades**, no certezas. No es un consejo de apuestas y no garantiza
ningún resultado.

---

## 📄 Licencia

Código abierto para uso personal y educativo. Gratuito.
