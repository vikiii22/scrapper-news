import argparse
import sys
from pathlib import Path

# Añadir el directorio src al path para poder importar los módulos
sys.path.append(str(Path(__file__).resolve().parent / 'src'))

def run_collect_data(args):
    """Ejecuta el script de recolección de datos."""
    print("Ejecutando recolección de datos...")
    from scripts.collect_data import main as collect_data_main
    collect_data_main()

def run_analyze_quiniela(args):
    """Ejecuta el script de análisis de la quiniela."""
    print("Ejecutando análisis de la quiniela...")
    from scripts.analyze_quiniela import main as analyze_quiniela_main
    analyze_quiniela_main()

def run_generate_predictions(args):
    """Ejecuta el script de generación de predicciones."""
    print("Ejecutando generación de predicciones...")
    from scripts.generate_predictions import main as generate_predictions_main
    generate_predictions_main()

def main():
    """Función principal del CLI."""
    parser = argparse.ArgumentParser(description="Quiniela Predictor CLI")
    subparsers = parser.add_subparsers(dest='command', required=True, help='Comandos disponibles')

    # Comando para recolectar datos
    parser_collect = subparsers.add_parser('collect', help='Recolecta todos los datos de las fuentes (scrapers).')
    parser_collect.set_defaults(func=run_collect_data)

    # Comando para analizar la quiniela
    parser_analyze = subparsers.add_parser('analyze', help='Analiza la quiniela de la jornada.')
    parser_analyze.set_defaults(func=run_analyze_quiniela)

    # Comando para generar predicciones
    parser_predict = subparsers.add_parser('predict', help='Genera predicciones para los próximos partidos.')
    parser_predict.set_defaults(func=run_generate_predictions)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
