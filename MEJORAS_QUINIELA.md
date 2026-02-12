# Mejoras en el Sistema de Predicción de Quinielas

## Nuevos Factores Avanzados (v2.0)

Se han añadido los siguientes factores para mejorar las predicciones:

### 1. Estadísticas Local/Visitante
- **Rendimiento en casa**: Puntos por partido jugando como local
- **Rendimiento fuera**: Puntos por partido jugando como visitante
- **Ajuste dinámico**: Si un equipo es muy fuerte en casa, aumenta su ventaja de local

### 2. Head-to-Head (H2H)
- Analiza los últimos enfrentamientos directos entre los dos equipos
- Favorece al equipo que históricamente domina el enfrentamiento
- Factor: -3 a +3 puntos según el dominio histórico

### 3. Climatología (Opcional)
- Integración con **OpenWeatherMap** (API gratuita)
- Considera lluvia, nieve, viento fuerte y temperaturas extremas
- Favorece al local en condiciones adversas (acostumbrado al clima)

### 4. Racha de Resultados
- Analiza los últimos 5 partidos de cada equipo
- Bonus por 3+ victorias consecutivas
- Penalización por 3+ derrotas consecutivas

### 5. Días de Descanso
- Considera diferencia de días de descanso entre equipos
- Penaliza si un equipo tiene menos de 3 días de descanso
- Favorece al equipo con más descanso

### 6. Importancia del Partido
- Lucha por título/Champions: +2 motivación
- Lucha por Europa: +1 motivación
- Evitar descenso: +2 motivación
- Zona tranquila: 0 motivación

---

## Configuración del Clima (Opcional pero Recomendado)

1. Registrarse en [OpenWeatherMap](https://openweathermap.org/api) (gratis)
2. Obtener API Key (límite: 1000 llamadas/día gratis)
3. Editar `scrapper/advanced_factors.py`:

```python
# Línea 23 aproximadamente
WEATHER_API_KEY = "tu_api_key_aqui"
```

---

## Uso

### Ejecutar análisis mejorado:
```bash
cd scrapper
python quiniela_analysis_v2.py
```

### Resultado:
- Archivo JSON: `data/apuestas_quiniela_mejoradas.json`
- Incluye probabilidades ajustadas con factores avanzados
- Indica si la predicción cambió respecto a la original

---

## Interpretación de Factores

En la salida verás algo como:
```
Factores: Local=+5.0 H2H=+0.0 Racha=+3.3 Total=+8.3
```

- **Local=+5.0**: Ventaja base de jugar en casa
- **H2H=+0.0**: Sin datos de enfrentamientos directos
- **Racha=+3.3**: El local tiene mejor forma reciente
- **Total=+8.3**: Suma de todos los factores (favorece al local)

### Factores destacados:
- `Racha: Local en forma` → El local viene de buena racha
- `H2H: Favorece local` → El local domina históricamente
- `Local muy fuerte en casa` → Gana mucho jugando de local

---

## Comparación de Versiones

| Característica | v1.0 | v2.0 |
|----------------|------|------|
| Posición en tabla | ✅ | ✅ |
| Diferencia de puntos | ✅ | ✅ |
| Forma últimos partidos | ✅ | ✅ |
| Estadísticas goles | ✅ | ✅ |
| **Stats local/visitante** | ❌ | ✅ |
| **Head-to-head** | ❌ | ✅ |
| **Climatología** | ❌ | ✅ |
| **Días de descanso** | ❌ | ✅ |
| **Importancia partido** | ❌ | ✅ |
| **Racha consecutiva** | ❌ | ✅ |

---

## Próximas Mejoras Posibles

1. **Lesiones y sanciones**: Integrar API de lesiones de jugadores clave
2. **Historial de árbitros**: Algunos árbitros favorecen más al local
3. **Cuotas de casas de apuestas**: Comparar con cuotas profesionales
4. **Machine Learning**: Entrenar modelo con resultados históricos

---

## Archivos Nuevos

- `scrapper/advanced_factors.py` - Módulo de factores avanzados
- `scrapper/quiniela_analysis_v2.py` - Script mejorado de análisis
- `data/cache/weather_cache.json` - Caché de clima (se crea automáticamente)
