"""
Script para generar HTML estático de la quiniela con las predicciones.
"""
import sys
from pathlib import Path
import json
from datetime import datetime

# Configurar sys.path
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from src.config.settings import PROCESSED_DATA_DIR
from src.config.settings import RAW_DATA_DIR
from src.scrapers.quiniela_html import QuinielaHtmlParser


def format_date(date_str: str) -> tuple[str, str]:
    """Convierte fecha ISO a formato día y hora."""
    date = datetime.fromisoformat(date_str)
    days = ['DOM', 'LUN', 'MAR', 'MIÉ', 'JUE', 'VIE', 'SÁB']
    day_name = days[date.weekday()]
    hour = date.strftime('%H:%M')
    return day_name, hour


def get_confidence_level(confidence: float) -> str:
    """Determina el nivel de confianza."""
    if confidence >= 40:
        return 'high'
    elif confidence >= 35:
        return 'medium'
    return 'low'


def load_quiniela_source_data() -> dict:
    """Carga los datos originales de la quiniela extraídos del HTML fuente."""
    source_path = RAW_DATA_DIR / "quiniela_matches.json"
    matches = []
    if source_path.exists():
        with open(source_path, 'r', encoding='utf-8') as f:
            matches = json.load(f)

    if not matches or not any(match.get('source_percentages') for match in matches):
        html_path = project_root / 'data' / 'Jornada_quiniela.html'
        if html_path.exists():
            matches = QuinielaHtmlParser(html_path).run()

    return {
        str(match.get('numero', index + 1)): match
        for index, match in enumerate(matches)
    }


def format_percentage_cell(cell: dict) -> str:
    """Renderiza una celda de porcentaje con su tendencia visual."""
    if not cell:
        return '<span class="source-value">-</span>'

    trend = cell.get('trend', 'flat')
    value = cell.get('value', '-')
    arrow = ''
    if trend == 'up':
        arrow = '<span class="source-trend up">▲</span>'
    elif trend == 'down':
        arrow = '<span class="source-trend down">▼</span>'

    return f'<span class="source-value">{value}</span>{arrow}'


def generate_source_percentages_html(source_match: dict) -> str:
    """Renderiza los porcentajes de la fuente original si están disponibles."""
    source_percentages = (source_match or {}).get('source_percentages', {})
    if not source_percentages:
        return ''

    sections = [
        ('Jugados', source_percentages.get('jugados')),
        ('LAE', source_percentages.get('lae')),
        ('Probables', source_percentages.get('probables')),
    ]

    section_html = []
    for label, values in sections:
        values = values or {}
        section_html.append(
            f"""
            <div class="source-block">
                <div class="source-block-label">{label}</div>
                <div class="source-block-values">
                    <div class="source-sign"><span>1</span>{format_percentage_cell(values.get('1'))}</div>
                    <div class="source-sign"><span>X</span>{format_percentage_cell(values.get('X'))}</div>
                    <div class="source-sign"><span>2</span>{format_percentage_cell(values.get('2'))}</div>
                </div>
            </div>"""
        )

    return f"""
            <div class="source-percentages">
                <div class="source-title">Datos originales de la web</div>
                <div class="source-grid">
                    {''.join(section_html)}
                </div>
            </div>"""


def generate_match_html(match: dict, index: int, source_match: dict | None = None) -> str:
    """Genera el HTML de un partido individual."""
    day, hour = format_date(match['match_info']['date'])
    confidence_level = get_confidence_level(match['confidence'])
    prediction = match['prediction']
    source_percentages_html = generate_source_percentages_html(source_match)
    
    return f"""
        <div class="match">
            <div class="match-header">
                <div class="match-number">{index + 1}</div>
                <div class="match-teams">
                    {match['match_info']['home_team']} - {match['match_info']['away_team']}
                </div>
                <div class="match-time">
                    <div class="match-day">{day}</div>
                    <div class="match-hour">{hour}</div>
                </div>
            </div>
            
            <div class="predictions">
                <button class="prediction-btn {'selected' if prediction == '1' else ''}">
                    1
                </button>
                <button class="prediction-btn {'selected' if prediction == 'X' else ''}">
                    X
                </button>
                <button class="prediction-btn {'selected' if prediction == '2' else ''}">
                    2
                </button>
            </div>
            {source_percentages_html}
            
            <div class="probabilities">
                <div class="prob-item">
                    <div class="prob-label">Local (1)</div>
                    <div class="prob-value">{match['probabilities']['home']:.1f}%</div>
                </div>
                <div class="prob-item">
                    <div class="prob-label">Empate (X)</div>
                    <div class="prob-value">{match['probabilities']['draw']:.1f}%</div>
                </div>
                <div class="prob-item">
                    <div class="prob-label">Visitante (2)</div>
                    <div class="prob-value">{match['probabilities']['away']:.1f}%</div>
                </div>
                <div class="prob-item">
                    <div class="prob-label">Confianza</div>
                    <div class="prob-value">
                        <span class="confidence {confidence_level}">
                            {match['confidence']:.1f}%
                        </span>
                    </div>
                </div>
            </div>
        </div>"""


def generate_static_html(data_path: Path, output_path: Path):
    """
    Genera un HTML estático con las predicciones de la quiniela.
    
    Args:
        data_path: Ruta al JSON con las predicciones
        output_path: Ruta donde guardar el HTML
    """
    # Cargar datos
    with open(data_path, 'r', encoding='utf-8') as f:
        quiniela_data = json.load(f)
    quiniela_source = load_quiniela_source_data()
    
    # Generar HTML de los partidos
    matches_html = '\n'.join([
        generate_match_html(match, idx, quiniela_source.get(str(idx + 1))) 
        for idx, match in enumerate(quiniela_data)
    ])
    
    # Timestamp actual
    now = datetime.now()
    timestamp = now.strftime('%d de %B de %Y - %H:%M')
    
    # Template completo
    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Quiniela - Predicciones IA</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <h1>🎯 Quiniela - Predicciones</h1>
            <div class="jornada">Jornada 45</div>
            <div class="timestamp">Actualizado: {timestamp}</div>
        </div>

        <!-- Legend -->
        <div class="legend">
            <div class="legend-item">
                <div class="legend-label">Probabilidades</div>
                <div class="legend-values">
                    <span>%1</span>
                    <span>%X</span>
                    <span>%2</span>
                </div>
            </div>
            <div class="legend-item">
                <div class="legend-label">Fuente Original</div>
                <div class="legend-values">
                    <span>Jugados</span>
                    <span>LAE</span>
                    <span>Probables</span>
                </div>
            </div>
        </div>

        <!-- Matches -->
        <div class="matches" id="matches-container">
{matches_html}
        </div>

        <!-- Footer -->
        <div class="footer">
            <p>Predicciones generadas por IA basadas en análisis de datos históricos</p>
            <p>🤖 Scrapper News © 2026 | Total de partidos: {len(quiniela_data)}</p>
        </div>
    </div>
</body>
</html>"""
    
    # Guardar HTML
    output_path.write_text(html_content, encoding='utf-8')
    print(f"✅ HTML estático generado en: {output_path}")
    print(f"   Total de partidos: {len(quiniela_data)}")


def main():
    """Función principal."""
    app_dir = project_root / "app"
    data_path = PROCESSED_DATA_DIR / "quiniela_predictions.json"
    output_path = app_dir / "quiniela.html"
    
    if not data_path.exists():
        print(f"❌ Error: No se encontró el archivo {data_path}")
        print("   Ejecuta primero: python scripts/analyze_quiniela.py")
        return
    
    generate_static_html(data_path, output_path)
    print(f"\n📂 Abre el archivo en tu navegador:")
    print(f"   {output_path.absolute()}")


if __name__ == "__main__":
    main()
