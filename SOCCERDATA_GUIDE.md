# Integración de SoccerData en tu Proyecto

## 📋 Resumen

**SoccerData** es una librería Python que permite obtener datos de fútbol de múltiples fuentes de forma sencilla y estandarizada. 

### ✅ Respuesta a tu pregunta: **SÍ, obtiene datos de la temporada actual (2025/26)**

He probado la librería y confirmado que:
- ✅ **Sofascore** funciona perfectamente con la temporada 2025/26
- ✅ Obtiene 380 partidos de La Liga (218 jugados, 162 pendientes)
- ✅ Datos actualizados en tiempo real
- ✅ También funciona con Premier League, Serie A, Bundesliga y Ligue 1
- ⚠️ FBref está bloqueado (Error 403), pero Sofascore es una excelente alternativa

## 🚀 Instalación

Ya está instalado en tu proyecto. Si necesitas instalarlo en otro entorno:

```bash
pip install soccerdata
```

## 📊 Resultados de la Prueba

### La Liga 2025/26 - Estadísticas Actuales:
- **Total partidos**: 380
- **Partidos jugados**: 218
- **Partidos pendientes**: 162
- **Total goles**: 568
- **Promedio goles/partido**: 2.61
- **Victorias local**: 103 (47.2%)
- **Empates**: 56 (25.7%)
- **Victorias visitante**: 59 (27.1%)

### Últimos Resultados (Jornada 22):
- Real Oviedo 1-0 Girona FC
- Athletic Club 1-1 Real Sociedad
- Getafe 0-0 Celta Vigo
- Real Betis 2-1 Valencia
- Real Madrid 2-1 Rayo Vallecano

## 💻 Uso Básico

### 1. Obtener Resultados de La Liga Actual

```python
import soccerdata as sd

# Inicializar para La Liga temporada 2025/26
sofascore = sd.Sofascore(leagues='ESP-La Liga', seasons='2526')

# Obtener calendario de partidos
schedule = sofascore.read_schedule()

# Ver últimos resultados
played = schedule[schedule['home_score'].notna()]
print(played.tail(5))

# Ver próximos partidos
upcoming = schedule[schedule['home_score'].isna()]
print(upcoming.head(5))
```

### 2. Usar el Script Integrado

He creado un script ya integrado en tu proyecto:

```bash
python scrapper/scrapper-soccerdata.py
```

Este script genera dos archivos JSON:
- `data/laliga_resultados_actuales.json` - Datos completos de La Liga
- `data/ligas_europeas_resultados.json` - Resumen de 5 ligas europeas

### 3. Importar en tus Scripts Existentes

```python
from scrapper.scrapper_soccerdata import obtener_resultados_laliga_actual

# Obtener datos actualizados
datos = obtener_resultados_laliga_actual()

# Usar los datos
if datos:
    print(f"Promedio de goles: {datos['estadisticas_generales']['promedio_goles_partido']}")
    print(f"Victorias local: {datos['estadisticas_generales']['victorias_local']}")
```

## 🔧 Fuentes de Datos Disponibles

| Fuente | Funciona | Datos Actuales | Notas |
|--------|----------|----------------|-------|
| **Sofascore** | ✅ | ✅ | Recomendado - Datos en tiempo real |
| **Understat** | ✅ | ✅ | Excelente para xG (expected goals) |
| **ClubElo** | ✅ | ✅ | Ratings ELO de equipos |
| FBref | ❌ | - | Bloqueado (Error 403) |
| WhoScored | ⚠️ | ⚠️ | Limitaciones de scraping |

## 📁 Estructura de Datos Generados

### laliga_resultados_actuales.json
```json
{
  "fecha_actualizacion": "2026-02-02 10:59:01",
  "temporada": "2025/26",
  "liga": "La Liga",
  "total_partidos": 380,
  "partidos_jugados": 218,
  "ultimos_resultados": [...],
  "proximos_partidos": [...],
  "estadisticas_generales": {
    "total_goles": 568,
    "promedio_goles_partido": 2.61,
    "victorias_local": 103,
    "empates": 56,
    "victorias_visitante": 59
  }
}
```

## 🎯 Casos de Uso en tu Proyecto

### 1. Actualización Diaria Automática
```bash
# Agregar a crontab o Task Scheduler
python scrapper/scrapper-soccerdata.py
```

### 2. Integración con Análisis de Quinielas
```python
# En scrapper-analysis.py
from scrapper_soccerdata import obtener_resultados_laliga_actual

datos = obtener_resultados_laliga_actual()

# Usar para mejorar predicciones
promedio_goles = datos['estadisticas_generales']['promedio_goles_partido']
porcentaje_local = datos['estadisticas_generales']['victorias_local'] / datos['partidos_jugados']
```

### 3. Validación de Datos
```python
# Comparar con tus scrapers actuales
datos_soccerdata = obtener_resultados_laliga_actual()
datos_besoccer = # tu scraper actual

# Validar consistencia
if datos_soccerdata['ultimos_resultados'][0] == datos_besoccer['ultimo_partido']:
    print("✅ Datos consistentes")
```

### 4. Análisis de Múltiples Ligas
```python
from scrapper_soccerdata import obtener_resultados_multiples_ligas

todas_ligas = obtener_resultados_multiples_ligas()

# Comparar ligas
for liga, datos in todas_ligas.items():
    print(f"{liga}: {datos['partidos_jugados']} partidos")
```

## 🔄 Otras Ligas Disponibles

```python
# Premier League
sofascore = sd.Sofascore('ENG-Premier League', '2526')

# Serie A
sofascore = sd.Sofascore('ITA-Serie A', '2526')

# Bundesliga
sofascore = sd.Sofascore('GER-Bundesliga', '2526')

# Ligue 1
sofascore = sd.Sofascore('FRA-Ligue 1', '2526')
```

## 📚 Documentación Oficial

- [Documentación completa](https://soccerdata.readthedocs.io/)
- [Guía de inicio rápido](https://soccerdata.readthedocs.io/en/latest/intro.html)
- [Ejemplos de uso](https://soccerdata.readthedocs.io/en/latest/datasources/)
- [Repositorio GitHub](https://github.com/probberechts/soccerdata)

## ⚠️ Consideraciones

1. **Rate Limiting**: Sofascore puede bloquear si haces demasiadas peticiones
2. **Cache Local**: Los datos se cachean localmente para evitar peticiones repetidas
3. **Uso Responsable**: Respeta los términos de servicio de las fuentes
4. **Actualizaciones**: Ejecuta el script periódicamente para datos actualizados

## 💡 Ventajas sobre tu Scraper Actual

| Aspecto | Tu Scraper | SoccerData |
|---------|------------|------------|
| Mantenimiento | Manual | Automático |
| Múltiples fuentes | No | Sí (6+ fuentes) |
| Datos estructurados | Depende del HTML | Siempre consistente |
| Datos históricos | Limitado | Amplio |
| Estadísticas avanzadas | No | Sí (xG, etc.) |

## 🎉 Conclusión

**SoccerData con Sofascore es una excelente solución para obtener datos de la temporada actual.** Puedes:

1. ✅ Complementar tus scrapers actuales
2. ✅ Obtener datos en tiempo real
3. ✅ Reducir el mantenimiento
4. ✅ Acceder a estadísticas avanzadas
5. ✅ Validar datos con múltiples fuentes

Los archivos generados ya están en `data/` y listos para usar.
