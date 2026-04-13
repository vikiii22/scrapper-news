# 🎯 Quiniela Pro - Sistema Profesional de Predicción

Sistema automatizado de predicción para la Quiniela española usando modelos estadísticos avanzados (Poisson + Dixon-Coles) con time-weighting y web scraping.

## 🚀 Características

- **Descarga Automática**: Obtiene datos históricos de La Liga (SP1.csv, SP2.csv) desde football-data.co.uk
- **Web Scraping Inteligente**: Extrae automáticamente los 15 partidos de la jornada desde eduardolosilla.es
- **Modelo Estadístico Avanzado**:
  - Distribución de Poisson para predicción de goles
  - Corrección Dixon-Coles para empates
  - Time-weighting con decaimiento exponencial (partidos recientes pesan más)
  - Boost del 10% en probabilidad de empate para partidos equilibrados
  - Ajustes manuales por cansancio de competición europea
- **Selección Inteligente**: Identifica automáticamente los 8 partidos con mayor certeza (menor entropía)
- **Salida Profesional**: Tabla formateada en terminal + archivo CSV exportable

## 📋 Requisitos

- Python 3.10 o superior
- Conexión a Internet (para descargar datos y scrapear partidos)

## 🔧 Instalación

1. **Clonar o descargar el proyecto**

```bash
cd scrapper-news-1
```

2. **Crear entorno virtual (recomendado)**

```bash
python -m venv .venv
source .venv/Scripts/activate  # Windows Git Bash
# o
.venv\Scripts\activate  # Windows CMD
# o
source .venv/bin/activate  # Linux/Mac
```

3. **Instalar dependencias**

```bash
pip install -r requirements.txt
```

## 🎮 Uso Básico

### Ejecutar predicción estándar

```bash
python quiniela_pro.py
```

Esto ejecutará el flujo completo:
1. Descarga SP1.csv y SP2.csv (si no existen)
2. Calcula estadísticas de equipos con time-weighting
3. Scrapea los partidos de la jornada desde eduardolosilla.es
4. Genera predicciones usando Poisson + Dixon-Coles
5. Selecciona los 8 mejores partidos
6. Muestra resultados en terminal
7. Guarda `jornada_prediccion.csv`

### Forzar descarga de datos actualizados

Para descargar los CSV incluso si ya existen localmente:

```python
# Modificar en main()
quiniela.run(force_download=True)
```

### Aplicar ajustes por competición europea

Si un equipo jugó Champions/Europa League esta semana:

```python
european_adjustments = {
    'Barcelona': -0.10,      # -10% fuerza de ataque
    'Real Madrid': -0.08,    # -8% fuerza de ataque
    'Ath Madrid': -0.05,     # -5% fuerza de ataque
}

quiniela.run(european_adjustments=european_adjustments)
```

## 📊 Interpretación de Resultados

### Columnas de salida

- **#**: Número de partido
- **Partido**: Equipo Local vs Equipo Visitante
- **Pred**: Predicción (1=Local, X=Empate, 2=Visitante)
- **Prob 1/X/2**: Probabilidades calculadas para cada resultado
- **Conf**: Confianza de la predicción (máxima probabilidad)
- **Entropía**: Medida de incertidumbre (menor = más certeza)

### Ejemplo de salida

```
====================================================================================================
                              TOP 8 APUESTAS RECOMENDADAS                              
====================================================================================================

+-----+--------------------------------+--------+----------+----------+----------+--------+-----------+
|   # | Partido                        | Pred   | Prob 1   | Prob X   | Prob 2   | Conf   | Entropía  |
+=====+================================+========+==========+==========+==========+========+===========+
|   1 | Barcelona vs Valladolid        | 1      | 78.3%    | 15.2%    | 6.5%     | 78.3%  | 0.812     |
+-----+--------------------------------+--------+----------+----------+----------+--------+-----------+
|   2 | Real Madrid vs Almeria         | 1      | 75.1%    | 17.3%    | 7.6%     | 75.1%  | 0.876     |
+-----+--------------------------------+--------+----------+----------+----------+--------+-----------+
...
```

## 🧮 Algoritmo Explicado

### 1. Time-Weighting

```python
weight = 0.95 ^ posición_partido
```

Los partidos más recientes tienen peso máximo (1.0), los antiguos decaen exponencialmente.

### 2. Fuerza de Ataque/Defensa

```
AS_equipo = goles_anotados_ponderados / promedio_liga
DS_equipo = goles_recibidos_ponderados / promedio_liga
```

### 3. Expected Goals (λ)

```
λ_local = AS_local × DS_visitante × factor_casa × promedio_liga
λ_visitante = AS_visitante × DS_local × promedio_liga
```

### 4. Poisson + Dixon-Coles

Se genera una matriz de probabilidades 7×7 (0-6 goles) aplicando:
- Distribución de Poisson básica
- Corrección Dixon-Coles para empates 0-0, 1-0, 0-1, 1-1
- Normalización de probabilidades

### 5. Boost de Empate

Si `λ_local + λ_visitante < 2.0` (partido cerrado):
```
P(X) = P(X) × 1.10
```

### 6. Selección por Entropía

```
Entropía = -Σ p_i × log₂(p_i)
```

Menor entropía = mayor certeza → Apuesta recomendada

## 🗂 Estructura del Proyecto

```
scrapper-news-1/
├── quiniela_pro.py          # Script principal
├── requirements.txt         # Dependencias
├── README.md               # Documentación
├── data/                   # Datos descargados (auto-creado)
│   ├── SP1.csv
│   └── SP2.csv
└── jornada_prediccion.csv  # Salida generada
```

## ⚙️ Configuración Avanzada

Puedes modificar los parámetros en el diccionario `CONFIG`:

```python
CONFIG = {
    'decay_factor': 0.95,      # Factor de decaimiento temporal (0.9-0.99)
    'draw_boost': 1.10,        # Multiplicador de empate (+5% a +15%)
    'low_xg_threshold': 2.0,   # Umbral de xG para boost de empate
    'num_picks': 8,            # Número de partidos a seleccionar (1-15)
}
```

## 🛠 Mapeo de Nombres de Equipos

El diccionario `TEAM_NAME_MAPPING` normaliza variantes:

```python
'AT.MADRID' → 'Ath Madrid'
'BARÇA' → 'Barcelona'
'R.MADRID' → 'Real Madrid'
```

Si el scraper encuentra un nombre no mapeado, puedes agregarlo al diccionario.

## 🐛 Solución de Problemas

### Error: "No se pudieron obtener partidos"

- Verifica conexión a Internet
- El script usa partidos de ejemplo como fallback
- Revisa si eduardolosilla.es cambió su estructura HTML

### Error: "No se pudo cargar ningún archivo CSV"

- Verifica conexión a Internet
- Comprueba que football-data.co.uk esté accesible
- Intenta ejecutar con `force_download=True`

### Advertencias de pandas/numpy

Son normales y están silenciadas con `warnings.filterwarnings('ignore')`

## 📈 Mejoras Futuras

- [ ] Integración con API de estadísticas en tiempo real
- [ ] Modelo de Machine Learning (XGBoost/Random Forest)
- [ ] Backtesting automático de predicciones pasadas
- [ ] Interfaz web con Flask/Streamlit
- [ ] Notificaciones por Telegram/Email
- [ ] Integración con casas de apuestas (odds reales)

## 📜 Licencia

Este proyecto es de código abierto y está disponible bajo licencia MIT.

## 👨‍💻 Autor

Desarrollado por un Senior Python Developer & Data Scientist especializado en apuestas deportivas.

## ⚠️ Disclaimer

Este software es solo para fines educativos y de investigación. Las apuestas deportivas conllevan riesgos financieros. Apuesta responsablemente.

---

**¿Preguntas o mejoras?** Abre un issue o envía un pull request 🚀
