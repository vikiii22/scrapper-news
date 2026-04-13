# ⚡ Inicio Rápido - Quiniela Pro

## 🎯 Instalación en 3 pasos

### 1. Activar entorno virtual (si existe)
```bash
# Windows Git Bash
source .venv/Scripts/activate

# Windows CMD
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate
```

### 2. Instalar dependencias
```bash
pip install requests beautifulsoup4 pandas numpy scipy tabulate
```

O usar el archivo de requisitos:
```bash
pip install -r requirements.txt
```

### 3. Ejecutar
```bash
python quiniela_pro.py
```

## 📊 Salida Esperada

```
================================================================================
                   🎯 QUINIELA PRO - Sistema Profesional de Predicción                   
================================================================================

📥 PASO 1: Descarga de datos históricos
✓ SP1.csv ya existe localmente
✓ SP2.csv ya existe localmente

📊 PASO 2: Procesamiento de datos históricos
✓ Cargados 380 registros desde SP1.csv
✓ Cargados 420 registros desde SP2.csv
✓ Estadísticas calculadas para 40 equipos

🌐 PASO 3: Extracción de partidos de la jornada
🌐 Scrapeando partidos desde https://www.eduardolosilla.es/...
✓ 15 partidos extraídos correctamente

🔮 PASO 4: Generación de predicciones
📊 Calculando fuerzas de ataque y defensa con time-weighting...

💎 PASO 5: Selección de mejores apuestas
✓ Seleccionados 8 partidos con mayor certeza

📋 PASO 6: Presentación de resultados

====================================================================================================
                                 TOP 8 APUESTAS RECOMENDADAS                                 
====================================================================================================

+-----+--------------------------------+--------+----------+----------+----------+--------+-----------+
|   # | Partido                        | Pred   | Prob 1   | Prob X   | Prob 2   | Conf   | Entropía  |
+=====+================================+========+==========+==========+==========+========+===========+
|   1 | Barcelona vs Real Madrid       | 1      | 78.3%    | 15.2%    | 6.5%     | 78.3%  | 0.812     |
+-----+--------------------------------+--------+----------+----------+----------+--------+-----------+
|   2 | Ath Madrid vs Sevilla          | 1      | 72.1%    | 18.3%    | 9.6%     | 72.1%  | 0.935     |
+-----+--------------------------------+--------+----------+----------+----------+--------+-----------+
...

✓ Resultados guardados en: jornada_prediccion.csv

================================================================================
                           ✅ PROCESO COMPLETADO EXITOSAMENTE                           
================================================================================
```

## 🎮 Comandos Útiles

### Ejecutar con ejemplos predefinidos
```bash
# Uso básico
python ejemplo_uso.py 1

# Con ajustes Champions
python ejemplo_uso.py 2

# Actualizar datos del servidor
python ejemplo_uso.py 3

# Configuración personalizada
python ejemplo_uso.py 4

# Solo top 5 favoritos
python ejemplo_uso.py 5
```

### Ejecutar tests
```bash
python test_basico.py
```

### Forzar descarga de datos frescos
Editar `quiniela_pro.py` línea ~765:
```python
quiniela.run(force_download=True)  # Cambiar False → True
```

## 📁 Archivos Generados

Después de ejecutar, se crearán:

```
data/
├── SP1.csv              # Primera División (descargado)
└── SP2.csv              # Segunda División (descargado)

jornada_prediccion.csv   # Predicciones CSV (generado)
```

## ⚙️ Personalización Rápida

### Cambiar número de apuestas
```python
# En quiniela_pro.py, modificar CONFIG:
'num_picks': 10,  # En vez de 8
```

### Aplicar cansancio por Champions
```python
# En main(), descomentar y editar:
european_adjustments = {
    'Barcelona': -0.10,    # -10% ataque
    'Real Madrid': -0.08,  # -8% ataque
}
```

### Ajustar agresividad del modelo
```python
# En quiniela_pro.py, CONFIG:
'decay_factor': 0.90,   # Más agresivo (90 en vez de 95)
'draw_boost': 1.15,     # Más empates predichos (15% en vez de 10%)
```

## 🐛 Solución Rápida de Problemas

### Error: ModuleNotFoundError
```bash
pip install -r requirements.txt
```

### Error: No se pueden scrapear partidos
- El script usará partidos de ejemplo automáticamente
- Verifica conexión a Internet
- Eduardo Losilla puede haber cambiado su web

### Error: No se pueden descargar CSV
- Verifica conexión a Internet
- football-data.co.uk puede estar caído
- Intenta más tarde o usa archivos locales

### Tests fallan
```bash
# Verifica que todas las dependencias estén instaladas
pip install --upgrade pandas numpy scipy requests beautifulsoup4 tabulate
```

## 📚 Documentación Completa

- **README.md**: Documentación detallada
- **MODELO_TECNICO.md**: Explicación matemática completa
- **ejemplo_uso.py**: 5 ejemplos de configuración

## 🚀 Próximos Pasos

1. ✅ Ejecutar primera predicción
2. 📊 Revisar resultados en CSV
3. 🧪 Experimentar con parámetros
4. 📈 Hacer backtesting con jornadas pasadas
5. 🎯 Refinar modelo según resultados

---

**¿Dudas?** Consulta [README.md](README.md) o [MODELO_TECNICO.md](MODELO_TECNICO.md)
