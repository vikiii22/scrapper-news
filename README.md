# AI Soccer Quiniela Predictor

Sistema avanzado de análisis y predicción de resultados de fútbol (La Liga y Segunda División), especializado en generar pronósticos para **La Quiniela** utilizando análisis multifactorial e IA simbólica.

## 🚀 Características Principales

El sistema utiliza un motor de predicción ponderado que evalúa múltiples factores para determinar la probabilidad de victoria (1, X, 2):

- **📊 Análisis de Clasificación (Nuevo):** Compara la "fuerza relativa" de los equipos basándose en su posición y puntos actuales en la tabla.
- **🤕 Impacto de Jugadores (Nuevo):**
  - Detecta **bajas/lesiones** en tiempo real scrapeando Sofascore.
  - Analiza la **calidad de la plantilla titular** comparando ratings promedio.
- **🌥️ Factor Climático:** Evalúa si la lluvia, viento o temperaturas extremas benefician al local o afectan al juego.
- **🏠 Factor Campo:** Pondera la ventaja de jugar en casa vs. el rendimiento visitante.
- **📈 Racha (Form):** Analiza los últimos 5 partidos y la tendencia de resultados.
- **⚔️ H2H (Cara a cara):** Histórico de enfrentamientos directos entre ambos equipos.
- **📅 Descanso:** Penalización por calendarios apretados (menos de 72h de descanso).
- **🏆 Importancia:** Detecta si un equipo se juega el título, Europa o el descenso.

## 🛠️ Tecnologías

- **Python 3.10+**
- **Playwright:** Scraping dinámico de alineaciones y bajas (Sofascore).
- **Pandas:** Procesamiento de datos estadísticos.
- **Pytest:** Testeo unitario.

## 📋 Requisitos e Instalación

1. **Clonar el repositorio:**
   ```bash
   git clone <repo-url>
   cd scrapper-news-1
   ```

2. **Crear entorno virtual (recomendado):**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   .venv\Scripts\activate     # Windows
   ```

3. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Instalar navegadores de Playwright:**
   Necesario para el scraping de jugadores.
   ```bash
   playwright install chromium
   ```

## 💻 Uso

### Generar Predicciones de la Quiniela
El comando principal descarga los datos más recientes, filtra los partidos del boleto actual de la Quiniela y genera el JSON de predicciones ordenado.

```bash
python main.py predict
```

Esto generará el archivo `data/processed/upcoming_match_predictions.json` con:
- Probabilidades % (1, X, 2).
- Confianza del pronóstico.
- Orden del boleto (1 al 15).

### Actualizar Datos (Scraping Manual)
Si solo quieres actualizar las bases de datos (clasificaciones, resultados históricos):

```bash
python main.py scrape
```

## ⚙️ Configuración

Puedes ajustar los pesos de los factores en `src/config/settings.py`:

```python
FACTOR_WEIGHTS = {
    "home_advantage": 1.0,    # Factor Campo
    "away_performance": -1.0, # Rendimiento Visitante
    "standings": 1.5,         # Posición en Tabla (Peso alto)
    "form": 0.8,              # Estado de forma reciente
    "h2h": 0.6,               # Histórico directo
    "weather": 0.3,           # Clima
    "players": 0.4,           # Bajas y calidad de plantilla
}
```

## 📂 Estructura del Proyecto

```
.
├── data/
│   ├── raw/          # Datos crudos (JSONs de Quiniela, Partidos, Clasificaciones)
│   └── processed/    # Resultados (Predicciones finales)
├── docs/             # Documentación adicional
├── scripts/          # Scripts de ejecución (generate_predictions.py, etc.)
├── src/
│   ├── analysis/     # Motor de predicción y factores (form, h2h, players...)
│   ├── config/       # Settings y constantes
│   ├── models/       # Clases de datos (Match, Player, Prediction)
│   ├── scrapers/     # Motores de scraping (Sofascore, Playwright, Weather)
│   └── utils/        # Utilidades generales
├── main.py           # Punto de entrada
└── requirements.txt
```