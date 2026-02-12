# 🏗️ Guía de Reestructuración del Proyecto - Quiniela Predictor

## 📋 Índice
1. [Estado Actual](#estado-actual)
2. [Nueva Estructura Propuesta](#nueva-estructura-propuesta)
3. [Descripción de Módulos](#descripción-de-módulos)
4. [Plan de Migración](#plan-de-migración)
5. [Convenciones de Código](#convenciones-de-código)
6. [Flujo de Datos](#flujo-de-datos)

---

## 📊 Estado Actual

### Problemas Identificados
| Problema | Impacto | Prioridad |
|----------|---------|-----------|
| Archivos con guiones en nombre (`scrapper-*.py`) | Dificulta imports | Alta |
| Código duplicado entre scrapers | Mantenimiento complejo | Alta |
| Sin separación de responsabilidades | Difícil testing | Media |
| Configuración dispersa | Errores de configuración | Media |
| Sin modelos de datos | Inconsistencia en estructuras | Media |

### Estructura Actual (Problemática)
```
scrapper-news-1/
├── main.py                          # ✅ Bueno: Orquestador central
├── scrapper/
│   ├── advanced_factors.py          # ⚠️ Muy grande (1000+ líneas)
│   ├── bot.py                       # ❓ Propósito unclear
│   ├── quiniela_analysis.py         # ⚠️ Versión antigua
│   ├── quiniela_analysis_v2.py      # ⚠️ Debería reemplazar v1
│   ├── scrapper-analysis.py         # ❌ Guión en nombre
│   ├── scrapper-data-besoccer.py    # ❌ Guión en nombre
│   ├── scrapper-futbol-espanol.py   # ❌ Guión en nombre
│   ├── scrapper-segunda-division.py # ❌ Guión en nombre
│   ├── scrapper-soccerdata.py       # ❌ Guión en nombre
│   ├── scrapper-teams-analysis.py   # ❌ Guión en nombre
│   ├── teams-scrapper.py            # ❌ Guión en nombre
│   ├── test-*.py                    # ⚠️ Tests mezclados con código
│   └── team_ids.json                # ⚠️ Config mezclada con código
├── data/                            # ✅ Bueno: Datos separados
└── example_data/                    # ✅ Bueno: Ejemplos separados
```

---

## 🎯 Nueva Estructura Propuesta

```
scrapper-news-1/
│
├── 📁 src/                          # Código fuente principal
│   ├── __init__.py
│   │
│   ├── 📁 config/                   # Configuración centralizada
│   │   ├── __init__.py
│   │   ├── settings.py              # Variables y constantes globales
│   │   └── team_ids.json            # IDs de equipos (desde scrapper/)
│   │
│   ├── 📁 scrapers/                 # Módulos de extracción de datos
│   │   ├── __init__.py
│   │   ├── base.py                  # Clase base abstracta
│   │   ├── sofascore.py             # API de Sofascore
│   │   ├── besoccer.py              # Scraping de BeSoccer
│   │   └── quiniela_html.py         # Parser del HTML de quiniela
│   │
│   ├── 📁 analysis/                 # Módulos de análisis
│   │   ├── __init__.py
│   │   ├── factors/                 # Factores de predicción
│   │   │   ├── __init__.py
│   │   │   ├── home_away.py         # Factor local/visitante
│   │   │   ├── form.py              # Factor racha
│   │   │   ├── h2h.py               # Factor head-to-head
│   │   │   ├── rest.py              # Factor días de descanso
│   │   │   └── importance.py        # Factor importancia partido
│   │   ├── predictor.py             # Motor de predicciones
│   │   └── quiniela.py              # Generador de apuestas
│   │
│   ├── 📁 models/                   # Modelos de datos (dataclasses)
│   │   ├── __init__.py
│   │   ├── match.py                 # Modelo Partido
│   │   ├── team.py                  # Modelo Equipo
│   │   ├── prediction.py            # Modelo Predicción
│   │   └── quiniela.py              # Modelo Boleto Quiniela
│   │
│   └── 📁 utils/                    # Utilidades compartidas
│       ├── __init__.py
│       ├── http_client.py           # Cliente HTTP con reintentos
│       ├── data_loader.py           # Carga y normalización de datos
│       ├── normalizers.py           # Normalización de nombres
│       └── formatters.py            # Formateo de salida (consola, JSON)
│
├── 📁 tests/                        # Tests unitarios y de integración
│   ├── __init__.py
│   ├── conftest.py                  # Fixtures compartidos
│   ├── test_scrapers/
│   │   └── test_sofascore.py
│   ├── test_analysis/
│   │   └── test_factors.py
│   └── test_models/
│       └── test_match.py
│
├── 📁 scripts/                      # Scripts ejecutables
│   ├── collect_data.py              # Recolectar todos los datos
│   ├── analyze_quiniela.py          # Análisis de quiniela
│   └── generate_predictions.py      # Generar predicciones
│
├── 📁 data/                         # Datos generados (gitignored)
│   ├── raw/                         # Datos sin procesar
│   ├── processed/                   # Datos procesados
│   └── predictions/                 # Predicciones generadas
│
├── 📁 example_data/                 # Datos de ejemplo (versionados)
│
├── 📁 docs/                         # Documentación adicional
│   ├── API.md                       # Documentación de APIs
│   └── ARCHITECTURE.md              # Arquitectura del sistema
│
├── main.py                          # CLI principal
├── requirements.txt
├── pyproject.toml                   # Configuración de proyecto moderna
├── README.md
└── GEMINI.md                        # Esta guía
```

---

## 📦 Descripción de Módulos

### 🔧 `src/config/settings.py`
Configuración centralizada del proyecto.

```python
"""Configuración global del proyecto."""
from pathlib import Path
from dataclasses import dataclass

# Rutas
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

# APIs
SOFASCORE_BASE_URL = "https://api.sofascore.com/api/v1"

# Ligas
@dataclass
class LeagueConfig:
    id: int
    season_id: int
    name: str
    country: str

LEAGUES = {
    "la_liga": LeagueConfig(id=54, season_id=77558, name="La Liga", country="Spain"),
    "segunda": LeagueConfig(id=55, season_id=77559, name="Segunda División", country="Spain"),
}

# Factores de predicción
FACTOR_WEIGHTS = {
    "home_advantage": 5.0,
    "form": 3.0,
    "h2h": 2.0,
    "rest_days": 1.5,
    "importance": 2.0,
}
```

### 🕷️ `src/scrapers/base.py`
Clase base abstracta para todos los scrapers.

```python
"""Clase base para scrapers."""
from abc import ABC, abstractmethod
from typing import Any, Dict, List
import logging

class BaseScraper(ABC):
    """Clase base abstracta para todos los scrapers."""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"scraper.{name}")
    
    @abstractmethod
    def fetch(self, **kwargs) -> Dict[str, Any]:
        """Obtiene datos de la fuente."""
        pass
    
    @abstractmethod
    def parse(self, raw_data: Any) -> List[Dict]:
        """Parsea los datos obtenidos."""
        pass
    
    def run(self, **kwargs) -> List[Dict]:
        """Ejecuta el scraper completo."""
        self.logger.info(f"Iniciando {self.name}")
        raw = self.fetch(**kwargs)
        parsed = self.parse(raw)
        self.logger.info(f"Completado: {len(parsed)} items")
        return parsed
```

### 📊 `src/models/match.py`
Modelo de datos para partidos.

```python
"""Modelo de datos para partidos."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict
from enum import Enum

class MatchStatus(Enum):
    SCHEDULED = "scheduled"
    LIVE = "live"
    FINISHED = "finished"
    POSTPONED = "postponed"

@dataclass
class Team:
    id: int
    name: str
    short_name: Optional[str] = None
    
@dataclass
class Match:
    id: int
    home_team: Team
    away_team: Team
    date: datetime
    league: str
    status: MatchStatus = MatchStatus.SCHEDULED
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    venue: Optional[str] = None
    round: Optional[int] = None
    
    @property
    def result(self) -> Optional[str]:
        """Retorna '1', 'X', o '2' según el resultado."""
        if self.home_score is None or self.away_score is None:
            return None
        if self.home_score > self.away_score:
            return "1"
        elif self.home_score < self.away_score:
            return "2"
        return "X"

@dataclass
class Prediction:
    match: Match
    prob_home: float
    prob_draw: float
    prob_away: float
    recommended_bet: str
    confidence: float
    factors: Dict[str, float] = field(default_factory=dict)
    
    @property
    def confidence_level(self) -> str:
        if self.confidence >= 70:
            return "ALTA"
        elif self.confidence >= 55:
            return "MEDIA"
        return "BAJA"
```

### 🧮 `src/analysis/factors/home_away.py`
Factor de rendimiento local/visitante.

```python
"""Factor de rendimiento local/visitante."""
from typing import Dict, List
from src.models.match import Match

def calculate_home_away_factor(
    team_name: str,
    matches: List[Match],
    is_home: bool,
    min_matches: int = 3
) -> Dict[str, float]:
    """
    Calcula el factor de rendimiento como local o visitante.
    
    Args:
        team_name: Nombre del equipo
        matches: Lista de partidos históricos
        is_home: True si juega en casa
        min_matches: Mínimo de partidos para calcular
        
    Returns:
        Dict con 'factor', 'wins', 'draws', 'losses', 'win_rate'
    """
    relevant_matches = [
        m for m in matches 
        if (is_home and m.home_team.name == team_name) or
           (not is_home and m.away_team.name == team_name)
    ]
    
    if len(relevant_matches) < min_matches:
        return {"factor": 0.0, "insufficient_data": True}
    
    wins = sum(1 for m in relevant_matches if _is_win(m, team_name, is_home))
    draws = sum(1 for m in relevant_matches if m.result == "X")
    losses = len(relevant_matches) - wins - draws
    
    win_rate = wins / len(relevant_matches)
    
    # Factor: diferencia respecto al 33% base
    base_rate = 0.33
    factor = (win_rate - base_rate) * 15  # Escalar a ±5 puntos máx
    
    return {
        "factor": round(factor, 2),
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "win_rate": round(win_rate * 100, 1),
        "matches_analyzed": len(relevant_matches)
    }

def _is_win(match: Match, team_name: str, is_home: bool) -> bool:
    """Determina si el equipo ganó el partido."""
    if match.result is None:
        return False
    if is_home:
        return match.result == "1"
    return match.result == "2"
```

### 🎯 `src/analysis/predictor.py`
Motor de predicciones.

```python
"""Motor de predicciones de partidos."""
from typing import Dict, List, Tuple
from dataclasses import dataclass
from src.models.match import Match, Prediction
from src.analysis.factors import home_away, form, h2h, rest, importance
from src.config.settings import FACTOR_WEIGHTS

@dataclass
class PredictionEngine:
    """Motor de predicciones."""
    
    historical_matches: List[Match]
    standings: Dict[str, Dict]
    
    def predict(self, match: Match) -> Prediction:
        """Genera predicción para un partido."""
        factors = self._calculate_all_factors(match)
        
        # Probabilidades base (equiprobables)
        probs = {"1": 33.33, "X": 33.33, "2": 33.33}
        
        # Ajustar por factores
        total_adjustment = sum(factors.values())
        probs["1"] += total_adjustment
        probs["2"] -= total_adjustment
        
        # Normalizar
        probs = self._normalize_probabilities(probs)
        
        # Determinar apuesta recomendada
        recommended = max(probs.items(), key=lambda x: x[1])
        
        return Prediction(
            match=match,
            prob_home=probs["1"],
            prob_draw=probs["X"],
            prob_away=probs["2"],
            recommended_bet=recommended[0],
            confidence=recommended[1],
            factors=factors
        )
    
    def _calculate_all_factors(self, match: Match) -> Dict[str, float]:
        """Calcula todos los factores para un partido."""
        return {
            "home_away": home_away.calculate_home_away_factor(
                match.home_team.name, 
                self.historical_matches, 
                is_home=True
            ).get("factor", 0),
            "form": form.calculate_form_factor(
                match.home_team.name,
                match.away_team.name,
                self.historical_matches
            ),
            "h2h": h2h.calculate_h2h_factor(
                match.home_team.name,
                match.away_team.name,
                self.historical_matches
            ),
            # ... más factores
        }
    
    def _normalize_probabilities(self, probs: Dict[str, float]) -> Dict[str, float]:
        """Normaliza probabilidades para que sumen 100."""
        # Asegurar valores positivos
        probs = {k: max(v, 1.0) for k, v in probs.items()}
        total = sum(probs.values())
        return {k: round(v / total * 100, 2) for k, v in probs.items()}
```

---

## 🔄 Plan de Migración

### Fase 1: Preparación (1-2 horas)
- [ ] Crear estructura de directorios
- [ ] Crear archivos `__init__.py`
- [ ] Configurar `pyproject.toml`
- [ ] Mover `team_ids.json` a `src/config/`

### Fase 2: Modelos (2-3 horas)
- [ ] Crear `src/models/match.py`
- [ ] Crear `src/models/team.py`
- [ ] Crear `src/models/prediction.py`
- [ ] Tests para modelos

### Fase 3: Utilidades (2-3 horas)
- [ ] Crear `src/utils/http_client.py`
- [ ] Crear `src/utils/data_loader.py`
- [ ] Crear `src/utils/normalizers.py` (mapeo de nombres de equipos)
- [ ] Tests para utilidades

### Fase 4: Scrapers (3-4 horas)
- [ ] Crear `src/scrapers/base.py`
- [ ] Migrar Sofascore → `src/scrapers/sofascore.py`
- [ ] Migrar BeSoccer → `src/scrapers/besoccer.py`
- [ ] Migrar parser HTML → `src/scrapers/quiniela_html.py`
- [ ] Tests para scrapers

### Fase 5: Factores (3-4 horas)
- [ ] Dividir `advanced_factors.py` en módulos separados
- [ ] `src/analysis/factors/home_away.py`
- [ ] `src/analysis/factors/form.py`
- [ ] `src/analysis/factors/h2h.py`
- [ ] `src/analysis/factors/rest.py`
- [ ] `src/analysis/factors/importance.py`
- [ ] Tests para factores

### Fase 6: Predictor (2-3 horas)
- [ ] Crear `src/analysis/predictor.py`
- [ ] Crear `src/analysis/quiniela.py`
- [ ] Tests de integración

### Fase 7: CLI y Scripts (2 horas)
- [ ] Actualizar `main.py`
- [ ] Crear scripts en `scripts/`
- [ ] Documentación final

---

## � Fase 8: Mejoras Avanzadas (Futuro)

### 🎭 Web Scraping con Playwright
Reemplazar scrapers basados en requests/selenium por **Playwright** para mayor robustez y capacidad de evadir detecciones.
- [ ] Implementar `src/scrapers/playwright_engine.py`
- [ ] Migrar scraping de BeSoccer y Sofascore dinámico
- [ ] Soporte para ejecución en headless/headed mode

### 👥 Análisis de Jugadores (Lineups & Stats)
Incorporar datos a nivel de jugador para refinar las predicciones:
- [ ] Extraer alineaciones probables y confirmadas.
- [ ] Estadísticas individuales (goles, asistencias, rating medio).
- [ ] Factor de "Jugadores Clave": Impacto de bajas/lesiones importantes.
- [ ] `src/analysis/factors/players.py`

### 🌤️ Datos Meteorológicos
Integrar previsiones del tiempo para el día y hora del partido:
- [ ] API de clima (ej. OpenWeatherMap).
- [ ] Análisis de impacto: ¿Cómo afecta la lluvia/viento a cada equipo? (ej. equipos técnicos sufren más con lluvia).
- [ ] `src/analysis/factors/weather.py`

---

## �📝 Convenciones de Código

### Nombrado
| Tipo | Convención | Ejemplo |
|------|------------|---------|
| Archivos | `snake_case.py` | `home_away.py` |
| Clases | `PascalCase` | `PredictionEngine` |
| Funciones | `snake_case` | `calculate_factor` |
| Constantes | `UPPER_SNAKE` | `BASE_URL` |
| Variables | `snake_case` | `match_data` |

### Docstrings
Usar formato Google:
```python
def calculate_factor(team: str, matches: List[Match]) -> float:
    """
    Calcula el factor de rendimiento para un equipo.
    
    Args:
        team: Nombre del equipo
        matches: Lista de partidos históricos
        
    Returns:
        Factor numérico entre -5 y +5
        
    Raises:
        ValueError: Si no hay suficientes partidos
    """
```

### Type Hints
Obligatorios en funciones públicas:
```python
def get_prediction(match_id: int) -> Optional[Prediction]:
    ...
```

### Imports
Orden estándar:
```python
# 1. Standard library
from datetime import datetime
from typing import Dict, List, Optional

# 2. Third party
import requests
from bs4 import BeautifulSoup

# 3. Local
from src.models.match import Match
from src.config.settings import BASE_URL
```

---

## 🔀 Flujo de Datos

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FLUJO DE DATOS                                     │
└─────────────────────────────────────────────────────────────────────────────┘

     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
     │   Sofascore  │     │   BeSoccer   │     │  HTML Quinela│
     │     API      │     │   Website    │     │    (LAE)     │
     └──────┬───────┘     └──────┬───────┘     └──────┬───────┘
            │                    │                    │
            ▼                    ▼                    ▼
     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
     │   Sofascore  │     │   BeSoccer   │     │   Quiniela   │
     │   Scraper    │     │   Scraper    │     │   Parser     │
     └──────┬───────┘     └──────┬───────┘     └──────┬───────┘
            │                    │                    │
            └────────────┬───────┴────────────────────┘
                         │
                         ▼
              ┌────────────────────┐
              │    Data Loader     │
              │  (Normalización)   │
              └─────────┬──────────┘
                        │
                        ▼
              ┌────────────────────┐
              │      Models        │
              │  Match, Team, etc  │
              └─────────┬──────────┘
                        │
            ┌───────────┼───────────┐
            ▼           ▼           ▼
     ┌──────────┐ ┌──────────┐ ┌──────────┐
     │Home/Away │ │   Form   │ │   H2H    │  ... más factores
     │  Factor  │ │  Factor  │ │  Factor  │
     └────┬─────┘ └────┬─────┘ └────┬─────┘
          │            │            │
          └────────────┼────────────┘
                       │
                       ▼
              ┌────────────────────┐
              │  Prediction Engine │
              │   (Combinación)    │
              └─────────┬──────────┘
                        │
                        ▼
              ┌────────────────────┐
              │  Quiniela Generator│
              │   (15 partidos)    │
              └─────────┬──────────┘
                        │
            ┌───────────┴───────────┐
            ▼                       ▼
     ┌──────────────┐       ┌──────────────┐
     │    JSON      │       │   Consola    │
     │   Output     │       │   Output     │
     └──────────────┘       └──────────────┘
```

---

## 🚀 Comandos Útiles

```bash
# Crear estructura de directorios
mkdir -p src/{config,scrapers,analysis/factors,models,utils}
mkdir -p tests/{test_scrapers,test_analysis,test_models}
mkdir -p scripts docs
mkdir -p data/{raw,processed,predictions}

# Crear archivos __init__.py
find src tests -type d -exec touch {}/__init__.py \;

# Ejecutar tests
pytest tests/ -v

# Ejecutar análisis completo
python -m scripts.analyze_quiniela

# Verificar tipos
mypy src/

# Formatear código
black src/ tests/
isort src/ tests/
```

---

## 📊 Mapeo de Archivos (Actual → Nuevo)

| Archivo Actual | Nuevo Ubicación | Notas |
|----------------|-----------------|-------|
| `scrapper/advanced_factors.py` | `src/analysis/factors/*.py` | Dividir en módulos |
| `scrapper/quiniela_analysis_v2.py` | `src/analysis/quiniela.py` | Refactorizar |
| `scrapper/quiniela_analysis.py` | ~~eliminar~~ | Obsoleto |
| `scrapper/scrapper-futbol-espanol.py` | `src/scrapers/sofascore.py` | Renombrar |
| `scrapper/scrapper-segunda-division.py` | `src/scrapers/sofascore.py` | Fusionar |
| `scrapper/scrapper-data-besoccer.py` | `src/scrapers/besoccer.py` | Renombrar |
| `scrapper/test-sofascore-complete.py` | `src/scrapers/sofascore.py` | Integrar |
| `scrapper/team_ids.json` | `src/config/team_ids.json` | Mover |
| `scrapper/bot.py` | ~~evaluar~~ | ¿Se usa? |
| `main.py` | `main.py` | Actualizar imports |

---

## ✅ Checklist de Calidad

Antes de considerar la migración completa:

- [ ] Todos los tests pasan
- [ ] Sin errores de tipo (mypy)
- [ ] Cobertura de tests > 80%
- [ ] Documentación actualizada
- [ ] `README.md` actualizado con nueva estructura
- [ ] Scripts funcionan igual que antes
- [ ] Datos de salida son idénticos

---

*Última actualización: 2026-02-10*
