# 🎯 Quiniela - Visualización Web

Aplicación web para visualizar las predicciones de la Quiniela generadas por IA.

## 📁 Estructura

```
app/
├── index.html          # HTML dinámico (carga datos via JavaScript)
├── quiniela.html       # HTML estático (datos pre-cargados)
├── styles.css          # Estilos CSS
├── app.js              # Lógica JavaScript
└── README.md           # Este archivo
```

## 🚀 Uso

### Opción 1: HTML Estático (Recomendado)

Genera un HTML con los datos ya integrados:

```bash
python scripts/generate_quiniela_html.py
```

Luego abre `app/quiniela.html` en tu navegador.

### Opción 2: HTML Dinámico

Requiere un servidor local para cargar el JSON vía AJAX:

```bash
# Opción A: Usando Python
cd app
python -m http.server 8000

# Opción B: Usando Node.js
cd app
npx http-server -p 8000
```

Luego visita: `http://localhost:8000/index.html`

## ✨ Características

- **Diseño Responsive**: Se adapta a móviles y tablets
- **Colores por Confianza**: 
  - 🟢 Verde: Alta confianza (≥40%)
  - 🟡 Amarillo: Media confianza (35-40%)
  - 🔴 Rojo: Baja confianza (<35%)
- **Interactivo**: Puedes cambiar las predicciones haciendo clic en los botones (solo en index.html)
- **Probabilidades**: Muestra las probabilidades de cada resultado

## 🎨 Personalización

### Cambiar colores

Edita `styles.css` y modifica las variables en el `:root` o las clases de gradiente:

```css
/* Cambiar color principal */
.header {
    background: linear-gradient(135deg, #TU_COLOR_1 0%, #TU_COLOR_2 100%);
}

/* Cambiar color del botón seleccionado */
.prediction-btn.selected {
    background: linear-gradient(135deg, #TU_COLOR 0%, #TU_COLOR_OSCURO 100%);
}
```

### Cambiar el número de jornada

Edita en `generate_quiniela_html.py` la línea:

```python
<div class="jornada">Jornada 45</div>  # Cambia el número aquí
```

O si usas `index.html`, edita directamente el HTML.

## 🔧 Desarrollo

### Regenerar HTML tras nuevas predicciones

Después de ejecutar el análisis de la quiniela:

```bash
python main.py  # o python scripts/analyze_quiniela.py
python scripts/generate_quiniela_html.py
```

### Estructura de datos esperada

El archivo `data/processed/quiniela_predictions.json` debe tener este formato:

```json
[
  {
    "match_info": {
      "home_team": "Equipo Local",
      "away_team": "Equipo Visitante",
      "date": "2026-02-28T14:00:00"
    },
    "prediction": "1",  // "1", "X", o "2"
    "confidence": 39.7,
    "probabilities": {
      "home": 38.5,
      "draw": 26.3,
      "away": 35.2
    }
  }
]
```

## 📊 Ejemplo de Uso Completo

```bash
# 1. Recolectar datos
python main.py collect

# 2. Analizar quiniela
python scripts/analyze_quiniela.py

# 3. Generar visualización
python scripts/generate_quiniela_html.py

# 4. Abrir en navegador
# Windows:
start app/quiniela.html

# macOS:
open app/quiniela.html

# Linux:
xdg-open app/quiniela.html
```

## 🐛 Troubleshooting

### Los datos no se cargan (index.html)

- Asegúrate de estar usando un servidor HTTP local
- Verifica que el archivo `data/processed/quiniela_predictions.json` existe
- Revisa la consola del navegador (F12) para ver errores

### El HTML estático no muestra datos

- Verifica que ejecutaste `python scripts/generate_quiniela_html.py`
- Confirma que existe el archivo de predicciones
- Revisa que no haya errores en la terminal al generar

## 📝 Licencia

Parte del proyecto Scrapper News © 2026
