"""
Interfaz de línea de comandos (CLI) para el predictor de fútbol.

Uso simple:
    python -m soccer_predictor.cli "Real Madrid" "Barcelona"

También acepta modo interactivo si no se pasan argumentos.
"""

import argparse
import sys

# En Windows la consola puede usar cp1252 y fallar con caracteres especiales.
# Fuerza UTF-8 en la salida estándar cuando sea posible.
if sys.platform.startswith("win"):
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Permitimos ejecutar tanto como script como módulo
try:
    from .orchestrator import predict
    from . import data_fetcher as df
except ImportError:
    from orchestrator import predict
    import data_fetcher as df


def print_prediction(result):
    """Imprime el resultado de la predicción de forma clara y formateada."""
    sep = "=" * 60
    print(sep)
    print(
        f"  {result['teams']['home'].upper()}  vs  "
        f"{result['teams']['away'].upper()}"
    )
    print(sep)
    print(f"  Competición: {result['competition']}")
    print(f"  Fecha:       {result['date']}")
    print(sep)

    # Predicción principal 1X2
    p = result["prob_1x2"]
    print("\n--- PREDICCIÓN 1X2 ---")
    print(f"  1. {result['teams']['home']}: {p['home']:.1%}")
    print(f"  X. Empate:           {p['draw']:.1%}")
    print(f"  2. {result['teams']['away']}: {p['away']:.1%}")
    print(f"  => Pronóstico: **{result['prediction_1x2']}**")

    print("\n--- MERCADOS ---")
    print(f"  Over/Under 2.5: {result['over_under']} ({result['over25_prob']:.1%})")
    print(f"  Ambos marcan:   {result['both_teams_score']} ({result['btts_prob']:.1%})")

    g = result["expected_goals"]
    print("\n--- GOLES ESPERADOS ---")
    print(
        f"  {result['teams']['home']}: {g['home']:.2f}  "
        f"//  {result['teams']['away']}: {g['away']:.2f}"
    )

    print("\n--- MOTIVACIÓN / RAZONAMIENTO ---")
    print(result["explanation"])
    src = result.get("explanation_source", "estadistica")
    print(f"\n(Fuente del razonamiento: {'LLM gratuito' if src == 'llm' else 'modelo estadístico'})")
    ds = result.get("data_sources", {})
    if ds:
        print(f"(Datos: local={ds.get('home')} [{ds.get('home_recent')}] vs "
              f"visitante={ds.get('away')} [{ds.get('away_recent')}])")
    print("\n" + sep)


def interactive_mode():
    """Modo interactivo paso a paso."""
    print("=== PREDICTOR DE FÚTBOL (gratuito) ===")
    print("Equipos disponibles:", ", ".join(df.get_available_teams()[:8]) + ", ...")
    print("(Puedes escribir cualquier equipo; se buscará en la base de datos)\n")

    home = input("Equipo local: ").strip()
    away = input("Equipo visitante: ").strip()

    if not home or not away:
        print("Debes indicar ambos equipos. Abortando.")
        sys.exit(1)

    competition = input("Competición (opcional): ").strip()
    date = input("Fecha (opcional, formato libre): ").strip()

    result = predict(home, away, competition, date)
    print_prediction(result)


def main():
    parser = argparse.ArgumentParser(description="Predictor de fútbol gratuito")
    parser.add_argument("home", nargs="?", help="Equipo local (cualquiera, se busca en vivo)")
    parser.add_argument("away", nargs="?", help="Equipo visitante (cualquiera)")
    parser.add_argument("-c", "--competition", default="", help="Competición")
    parser.add_argument("-d", "--date", default="", help="Fecha del partido")
    parser.add_argument(
        "-v", "--venue",
        default="home",
        choices=["home", "neutral", "away"],
        help="Sede del partido (default: home)",
    )
    parser.add_argument("--no-live", action="store_true", help="No buscar en internet, solo caché+estático")
    parser.add_argument("--refresh", action="store_true", help="Ignorar caché JSON y re-descargar")
    parser.add_argument("--news", action="store_true", help="Incluir noticias recientes (lesiones/forma)")
    parser.add_argument("--fetch-only", action="store_true", help="Solo descargar y guardar en BBDD, sin predecir")
    parser.add_argument("--db-stats", action="store_true", help="Mostrar estado de la BBDD JSON y salir")

    args = parser.parse_args()

    if args.db_stats:
        try:
            from . import database as db
        except ImportError:
            import database as db
        s = db.stats()
        print(f"BBDD en: {s['db_dir']}")
        print(f"  Equipos guardados: {s['teams']}")
        print(f"  Parejas H2H:       {s['h2h_pairs']}")
        print(f"  Pronósticos log:   {s['predictions']}")
        return

    if args.home and args.away:
        if args.fetch_only:
            for t in (args.home, args.away):
                rec = df.fetch_and_store(t, with_news=args.news)
                print(f"{t}: {'guardado (' + rec.get('source', '?') + ')' if rec else 'SIN DATOS en vivo, se usará estático'}")
            return
        # Modo directo por argumentos
        result = predict(
            args.home, args.away, args.competition, args.date, args.venue,
            live=not args.no_live, with_news=args.news, refresh=args.refresh,
        )
        print_prediction(result)
    else:
        interactive_mode()


if __name__ == "__main__":
    main()
