# 📐 Documentación Técnica: Modelo Estadístico Quiniela Pro

## Fundamentos Matemáticos

### 1. Distribución de Poisson

El modelo base asume que los goles en fútbol siguen una distribución de Poisson:

```
P(X = k) = (λ^k × e^-λ) / k!
```

Donde:
- `k` = número de goles
- `λ` = expected goals (xG)
- `e` = constante de Euler (2.71828...)

**Ventaja**: Captura la naturaleza discreta y rara de los goles en fútbol.

### 2. Fuerza de Ataque y Defensa

Para cada equipo calculamos dos métricas normalizadas:

#### Attack Strength (AS)
```
AS = (goles_anotados_ponderados / partidos_ponderados) / promedio_liga
```

- `AS > 1`: Ataque superior a la media
- `AS = 1`: Ataque promedio
- `AS < 1`: Ataque inferior a la media

#### Defense Strength (DS)
```
DS = (goles_recibidos_ponderados / partidos_ponderados) / promedio_liga
```

- `DS > 1`: Defensa débil (recibe más goles)
- `DS = 1`: Defensa promedio
- `DS < 1`: Defensa sólida

**Nota**: A diferencia del ataque, en defensa valores bajos son mejores.

### 3. Time-Weighting (Decay Exponencial)

Los partidos recientes tienen más relevancia que los antiguos:

```
weight[i] = decay_factor ^ i
```

Donde `i` es la posición del partido (0 = más reciente).

**Ejemplo con decay_factor = 0.95:**
- Partido más reciente: peso = 1.00
- Hace 5 partidos: peso = 0.77
- Hace 10 partidos: peso = 0.60
- Hace 20 partidos: peso = 0.36

**Ventaja**: Captura cambios de forma, lesiones, cambios de entrenador.

### 4. Expected Goals (λ)

Para un partido Local vs Visitante:

```
λ_local = AS_local × DS_visitante × factor_casa × promedio_liga
λ_visitante = AS_visitante × DS_local × promedio_liga
```

**Factor de casa**: Típicamente 1.2 (20% ventaja)

**Interpretación**:
- Un equipo con buen ataque (`AS` alto) que juega contra defensa débil (`DS` alto) tendrá `λ` alto
- La ventaja de jugar en casa multiplica el `λ` del equipo local

### 5. Corrección Dixon-Coles

El modelo Poisson básico subestima empates con pocos goles. Dixon-Coles aplica un factor de corrección:

```python
τ = 0.1  # parámetro típico

Si (local=0, visitante=0): factor = 1 - λ_local × λ_visitante × τ
Si (local=0, visitante=1): factor = 1 + λ_local × τ
Si (local=1, visitante=0): factor = 1 + λ_visitante × τ
Si (local=1, visitante=1): factor = 1 - τ
Otro caso: factor = 1.0
```

**Efecto**: Aumenta probabilidad de 0-0, 1-1 en partidos equilibrados.

### 6. Matriz de Probabilidades

Calculamos probabilidades para todas las combinaciones (0-6 goles):

```python
for i in range(7):
    for j in range(7):
        prob_base = poisson.pmf(i, λ_local) × poisson.pmf(j, λ_visitante)
        prob_corregida = prob_base × dixon_coles_correction(i, j)
```

Luego normalizamos para que sumen 1.0.

### 7. Probabilidades 1-X-2

A partir de la matriz 7×7:

```
P(1) = Σ prob[i][j] donde i > j  (victorias locales)
P(X) = Σ prob[i][i]              (empates)
P(2) = Σ prob[i][j] donde i < j  (victorias visitantes)
```

### 8. Boost de Empate

Para partidos con expected goals bajo (defensivos/equilibrados):

```python
if λ_local + λ_visitante < threshold:
    P(X) = P(X) × boost_factor
    # Renormalizar
```

**Ejemplo**: Si `threshold = 2.0` y `boost = 1.10`:
- Partido con λ_local=0.9, λ_visitante=0.8 → suma=1.7 < 2.0
- P(X) aumenta un 10%

**Justificación**: Partidos cerrados tienden más al empate de lo que predice Poisson puro.

### 9. Ajustes por Competición Europea

Para equipos que jugaron Champions/Europa League a mitad de semana:

```python
λ_ajustado = λ_base × (1 + adjustment)
```

**Ejemplo**: 
- `adjustment = -0.10` → λ reducido en 10%
- Barcelona con λ=2.5 → 2.5 × 0.90 = 2.25

**Justificación**: Cansancio físico y mental reduce rendimiento ofensivo.

### 10. Entropía de Shannon

Medida de incertidumbre de la predicción:

```
H = -Σ p_i × log₂(p_i)
```

**Interpretación**:
- `H = 0`: Certeza total (una probabilidad = 1, otras = 0)
- `H = 1.58`: Máxima incertidumbre (33.3%, 33.3%, 33.3%)

**Uso**: Seleccionamos partidos con menor entropía (mayor certeza).

## Ejemplo Completo de Cálculo

### Partido: Barcelona (Local) vs Getafe (Visitante)

#### Datos históricos (con time-weighting):
- Barcelona: AS = 1.45, DS = 0.70
- Getafe: AS = 0.85, DS = 1.15
- Promedio liga: 1.5 goles/equipo/partido
- Factor casa: 1.2

#### Paso 1: Calcular λ
```
λ_Barcelona = 1.45 × 1.15 × 1.2 × 1.5 = 3.00
λ_Getafe = 0.85 × 0.70 × 1.5 = 0.89
```

#### Paso 2: Matriz Poisson (ejemplo 3x3)
```
         Getafe: 0      1       2
Barça 0:  0.050   0.044   0.020
     1:  0.150   0.134   0.060
     2:  0.224   0.200   0.089
     3:  0.224   0.200   0.089
     ...
```

#### Paso 3: Aplicar Dixon-Coles
```
P(0-0) ajustado = 0.050 × (1 - 3.00×0.89×0.1) = 0.050 × 0.733 = 0.037
P(1-1) ajustado = 0.134 × (1 - 0.1) = 0.134 × 0.90 = 0.121
...
```

#### Paso 4: Sumar probabilidades
```
P(1) = suma de i>j = 0.724 (72.4%)
P(X) = suma diagonal = 0.189 (18.9%)
P(2) = suma de i<j = 0.087 (8.7%)
```

#### Paso 5: Verificar boost de empate
```
λ_total = 3.00 + 0.89 = 3.89 > 2.0
→ No se aplica boost (partido no es bajo scoring)
```

#### Paso 6: Predicción final
```
Predicción: 1 (Victoria Barcelona)
Confianza: 72.4%
Entropía: -(0.724×log₂(0.724) + 0.189×log₂(0.189) + 0.087×log₂(0.087))
        = 0.91 bits
```

## Calibración del Modelo

### Parámetros Críticos

| Parámetro | Rango | Óptimo | Efecto |
|-----------|-------|--------|--------|
| `decay_factor` | 0.85-0.99 | 0.95 | Mayor = más memoria histórica |
| `draw_boost` | 1.05-1.20 | 1.10 | Mayor = más empates predichos |
| `low_xg_threshold` | 1.5-2.5 | 2.0 | Mayor = boost en más partidos |
| `τ (Dixon-Coles)` | 0.08-0.15 | 0.10 | Mayor = más corrección en empates |
| `factor_casa` | 1.15-1.30 | 1.20 | Mayor = más ventaja local |

### Validación Recomendada

Para calibrar el modelo, realizar backtesting:

1. Separar datos en train (80%) / test (20%)
2. Entrenar modelo con datos históricos
3. Predecir jornadas del test set
4. Calcular métricas:
   - **Accuracy**: % de predicciones correctas
   - **ROI**: Retorno de inversión (simulando apuestas)
   - **Brier Score**: Error cuadrático de probabilidades
   - **Log Loss**: Pérdida logarítmica

## Limitaciones del Modelo

1. **No considera**:
   - Lesiones de jugadores clave
   - Expulsiones
   - Motivación (descenso, Champions)
   - Condiciones meteorológicas
   - Árbitro

2. **Supuestos**:
   - Independencia de goles (no siempre real)
   - Distribución de Poisson (aproximación)
   - Estacionariedad de forma (puede cambiar rápido)

3. **Datos**:
   - Calidad depende de football-data.co.uk
   - Equipos ascendidos tienen poco historial
   - Cambios de entrenador no se capturan instantáneamente

## Referencias Académicas

1. **Dixon, M. J., & Coles, S. G. (1997)**  
   *"Modelling Association Football Scores and Inefficiencies in the Football Betting Market"*  
   Journal of the Royal Statistical Society: Series C (Applied Statistics), 46(2), 265-280.

2. **Maher, M. J. (1982)**  
   *"Modelling association football scores"*  
   Statistica Neerlandica, 36(3), 109-118.

3. **Rue, H., & Salvesen, Ø. (2000)**  
   *"Prediction and retrospective analysis of soccer matches in a league"*  
   Journal of the Royal Statistical Society: Series D (The Statistician), 49(3), 399-418.

## Código de Ejemplo: Cálculo Manual

```python
import numpy as np
from scipy.stats import poisson

def predict_match_manual(lambda_home, lambda_away, max_goals=6):
    """Ejemplo simplificado de predicción"""
    
    # Matriz de probabilidades
    prob_matrix = np.zeros((max_goals+1, max_goals+1))
    
    for i in range(max_goals+1):
        for j in range(max_goals+1):
            prob_matrix[i][j] = poisson.pmf(i, lambda_home) * poisson.pmf(j, lambda_away)
    
    # Normalizar
    prob_matrix /= prob_matrix.sum()
    
    # Calcular 1-X-2
    home_win = np.tril(prob_matrix, -1).sum()
    draw = np.trace(prob_matrix)
    away_win = np.triu(prob_matrix, 1).sum()
    
    return home_win, draw, away_win

# Ejemplo
p1, px, p2 = predict_match_manual(2.1, 1.3)
print(f"P(1)={p1:.2%}, P(X)={px:.2%}, P(2)={p2:.2%}")
```

---

**Autor**: Senior Data Scientist - Quiniela Pro  
**Última actualización**: 2026
