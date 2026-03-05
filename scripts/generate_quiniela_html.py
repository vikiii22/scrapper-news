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


def generate_match_html(match: dict, index: int) -> str:
    """Genera el HTML de un partido individual."""
    day, hour = format_date(match['match_info']['date'])
    confidence_level = get_confidence_level(match['confidence'])
    prediction = match['prediction']
    
    # Generar sección de datos de Losilla si están disponibles
    losilla_html = ""
    if 'losilla_data' in match:
        losilla = match['losilla_data']
        
        # Preparar datos de cada tipo
        jugados = losilla.get('jugados', {})
        probables = losilla.get('probables', {})
        lae = losilla.get('lae', {})
        
        # Solo mostrar si hay al menos un tipo de datos disponibles
        if jugados or probables or lae:
            losilla_html = '<div class="losilla-section">'
            losilla_html += '<div class="losilla-header">📊 Datos Recopilados de Jugadores</div>'
            losilla_html += '<div class="losilla-grid">'
            
            if probables:
                losilla_html += f'''
                <div class="losilla-type">
                    <div class="losilla-type-title">📈 %Probables (Estadísticas Liga)</div>
                    <div class="losilla-values">
                        <span class="losilla-val">1: {probables.get("1", 0):.1f}%</span>
                        <span class="losilla-val">X: {probables.get("X", 0):.1f}%</span>
                        <span class="losilla-val">2: {probables.get("2", 0):.1f}%</span>
                    </div>
                </div>'''
            
            if jugados:
                losilla_html += f'''
                <div class="losilla-type">
                    <div class="losilla-type-title">👥 %Jugados (Comunidad)</div>
                    <div class="losilla-values">
                        <span class="losilla-val">1: {jugados.get("1", 0):.1f}%</span>
                        <span class="losilla-val">X: {jugados.get("X", 0):.1f}%</span>
                        <span class="losilla-val">2: {jugados.get("2", 0):.1f}%</span>
                    </div>
                </div>'''
            
            if lae:
                losilla_html += f'''
                <div class="losilla-type">
                    <div class="losilla-type-title">🎰 %LAE (Oficial)</div>
                    <div class="losilla-values">
                        <span class="losilla-val">1: {lae.get("1", 0):.1f}%</span>
                        <span class="losilla-val">X: {lae.get("X", 0):.1f}%</span>
                        <span class="losilla-val">2: {lae.get("2", 0):.1f}%</span>
                    </div>
                </div>'''
            
            losilla_html += '</div></div>'
    
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
            {losilla_html}
        </div>"""


from src.utils.mongo_loader import load_mongo_data

def generate_static_html(output_path: Path):
    """
    Genera un HTML estático con las predicciones de la quiniela.
    
    Args:
        output_path: Ruta donde guardar el HTML
    """
    # Cargar datos
    quiniela_data = load_mongo_data("quiniela_predictions")
    if not quiniela_data:
        raise ValueError("No se encontraron predicciones en MongoDB.")
    
    # Generar HTML de los partidos
    matches_html = '\n'.join([
        generate_match_html(match, idx) 
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
                <div class="legend-label">Predicciones IA</div>
                <div class="legend-values">
                    <span>%1</span>
                    <span>%X</span>
                    <span>%2</span>
                </div>
            </div>
            <div class="legend-item">
                <div class="legend-label">Datos Jugadores</div>
                <div class="legend-values">
                    <span>📈 Probables</span>
                    <span>👥 Jugados</span>
                    <span>🎰 LAE</span>
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
    output_path = app_dir / "quiniela.html"
    
    try:
        generate_static_html(output_path)
    except Exception as e:
        print(f"❌ Error: {e}")
        print("   Ejecuta primero: python main.py analyze")
        return
    print(f"\n📂 Abre el archivo en tu navegador:")
    print(f"   {output_path.absolute()}")


if __name__ == "__main__":
    main()
