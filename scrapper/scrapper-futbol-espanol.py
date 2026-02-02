"""
Script principal para obtener y analizar datos de fútbol español
Primera División (La Liga) y Segunda División
"""
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime

# Configuración
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SCRAPPER_DIR = BASE_DIR / "scrapper"


def ejecutar_script(script_name, descripcion):
    """Ejecuta un script de scrapping"""
    print("\n" + "="*70)
    print(f"EJECUTANDO: {descripcion}")
    print("="*70)
    
    script_path = SCRAPPER_DIR / script_name
    
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=300  # 5 minutos máximo
        )
        
        if result.returncode == 0:
            print(f"✓ {descripcion} completado exitosamente")
            return True
        else:
            print(f"✗ Error en {descripcion}")
            print(result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print(f"✗ Timeout en {descripcion}")
        return False
    except Exception as e:
        print(f"✗ Error ejecutando {descripcion}: {str(e)}")
        return False


def calcular_probabilidades_partido(equipo_local, equipo_visitante, clasificacion, partidos_jugados):
    """
    Calcula probabilidades de V/E/D para un partido específico
    """
    # Buscar datos de ambos equipos en la clasificación
    datos_local = next((e for e in clasificacion if e['equipo'] == equipo_local), None)
    datos_visitante = next((e for e in clasificacion if e['equipo'] == equipo_visitante), None)
    
    if not datos_local or not datos_visitante:
        return None
    
    # 1. Factor posición en tabla (0-10 puntos)
    factor_posicion = (datos_visitante['posicion'] - datos_local['posicion']) / len(clasificacion) * 10
    
    # 2. Factor diferencia de puntos (0-10 puntos)
    diferencia_puntos = datos_local['puntos'] - datos_visitante['puntos']
    factor_puntos = min(max(diferencia_puntos / 3, -10), 10)
    
    # 3. Factor forma (últimos 5 partidos) (0-10 puntos)
    forma_local = calcular_forma_equipo(equipo_local, partidos_jugados[-15:])
    forma_visitante = calcular_forma_equipo(equipo_visitante, partidos_jugados[-15:])
    factor_forma = (forma_local - forma_visitante) * 2
    
    # 4. Factor goles (0-10 puntos)
    ratio_goles_local = datos_local['promedio_goles_favor'] - datos_local['promedio_goles_contra']
    ratio_goles_visitante = datos_visitante['promedio_goles_favor'] - datos_visitante['promedio_goles_contra']
    factor_goles = (ratio_goles_local - ratio_goles_visitante) * 5
    
    # 5. Factor local/visitante (ventaja de jugar en casa: +5 base)
    factor_localidad = 5
    
    # 6. Factor porcentaje de victorias
    factor_victorias = (datos_local['porcentaje_victorias'] - datos_visitante['porcentaje_victorias']) / 10
    
    # Calcular puntuación total
    puntuacion_total = (
        factor_posicion +
        factor_puntos +
        factor_forma +
        factor_goles +
        factor_localidad +
        factor_victorias
    )
    
    # Convertir puntuación a probabilidades (escala -30 a +30)
    # -30 = 0% victoria local, +30 = 100% victoria local
    prob_victoria_local = 50 + (puntuacion_total * 1.5)
    prob_victoria_local = max(10, min(80, prob_victoria_local))  # Limitar entre 10% y 80%
    
    # Probabilidad de empate (base 25%, ajustada según competitividad)
    competitividad = abs(puntuacion_total)
    prob_empate = 25 - (competitividad * 0.3)
    prob_empate = max(10, min(35, prob_empate))
    
    # Probabilidad de victoria visitante (resto)
    prob_victoria_visitante = 100 - prob_victoria_local - prob_empate
    
    # Ajustar para que sume exactamente 100
    total = prob_victoria_local + prob_empate + prob_victoria_visitante
    prob_victoria_local = round((prob_victoria_local / total) * 100, 2)
    prob_empate = round((prob_empate / total) * 100, 2)
    prob_victoria_visitante = round((prob_victoria_visitante / total) * 100, 2)
    
    # Determinar predicción principal
    max_prob = max(prob_victoria_local, prob_empate, prob_victoria_visitante)
    if max_prob == prob_victoria_local:
        prediccion = 'V'
        confianza = prob_victoria_local
    elif max_prob == prob_empate:
        prediccion = 'E'
        confianza = prob_empate
    else:
        prediccion = 'D'
        confianza = prob_victoria_visitante
    
    return {
        'equipo_local': equipo_local,
        'equipo_visitante': equipo_visitante,
        'probabilidades': {
            'victoria_local': prob_victoria_local,
            'empate': prob_empate,
            'victoria_visitante': prob_victoria_visitante
        },
        'prediccion': prediccion,
        'confianza': confianza,
        'factores': {
            'posicion': round(factor_posicion, 2),
            'puntos': round(factor_puntos, 2),
            'forma': round(factor_forma, 2),
            'goles': round(factor_goles, 2),
            'localidad': factor_localidad,
            'victorias': round(factor_victorias, 2),
            'total': round(puntuacion_total, 2)
        },
        'datos_equipos': {
            'local': {
                'posicion': datos_local['posicion'],
                'puntos': datos_local['puntos'],
                'forma': forma_local,
                'goles_favor': datos_local['promedio_goles_favor'],
                'goles_contra': datos_local['promedio_goles_contra']
            },
            'visitante': {
                'posicion': datos_visitante['posicion'],
                'puntos': datos_visitante['puntos'],
                'forma': forma_visitante,
                'goles_favor': datos_visitante['promedio_goles_favor'],
                'goles_contra': datos_visitante['promedio_goles_contra']
            }
        }
    }


def calcular_forma_equipo(equipo, ultimos_partidos):
    """
    Calcula la forma de un equipo en sus últimos partidos
    Victoria = 3 puntos, Empate = 1 punto, Derrota = 0 puntos
    Retorna puntuación de 0-5
    """
    partidos_equipo = []
    
    for partido in ultimos_partidos:
        if partido['equipo_local'] == equipo:
            if partido.get('goles_local', 0) > partido.get('goles_visitante', 0):
                partidos_equipo.append(3)
            elif partido.get('goles_local', 0) == partido.get('goles_visitante', 0):
                partidos_equipo.append(1)
            else:
                partidos_equipo.append(0)
        elif partido['equipo_visitante'] == equipo:
            if partido.get('goles_visitante', 0) > partido.get('goles_local', 0):
                partidos_equipo.append(3)
            elif partido.get('goles_visitante', 0) == partido.get('goles_local', 0):
                partidos_equipo.append(1)
            else:
                partidos_equipo.append(0)
    
    # Tomar últimos 5 partidos
    ultimos_5 = partidos_equipo[-5:] if len(partidos_equipo) >= 5 else partidos_equipo
    
    if not ultimos_5:
        return 2.5  # Neutral
    
    # Retornar promedio (0-5 escala)
    return sum(ultimos_5) / 3  # Divide por 3 para escalar de 0-15 a 0-5


def predecir_proximos_partidos(datos_liga, liga_nombre):
    """
    Genera predicciones para todos los próximos partidos de una liga
    """
    proximos = datos_liga.get('proximos_partidos', [])
    if not proximos:
        return []
    
    clasificacion = datos_liga.get('clasificacion', [])
    partidos_jugados = datos_liga.get('todos_partidos_jugados', [])
    
    predicciones = []
    
    for partido in proximos:
        prediccion = calcular_probabilidades_partido(
            partido['equipo_local'],
            partido['equipo_visitante'],
            clasificacion,
            partidos_jugados
        )
        
        if prediccion:
            prediccion['partido_id'] = partido.get('id')
            prediccion['jornada'] = partido.get('jornada')
            prediccion['fecha'] = partido.get('fecha')
            prediccion['liga'] = liga_nombre
            predicciones.append(prediccion)
    
    return predicciones


def generar_reporte_predicciones(predicciones, liga_nombre):
    """
    Muestra las predicciones en consola
    """
    if not predicciones:
        print(f"\nNo hay próximos partidos para {liga_nombre}")
        return
    
    print(f"\n{'='*70}")
    print(f"PREDICCIONES {liga_nombre.upper()}")
    print(f"{'='*70}")
    
    for pred in predicciones:
        print(f"\n{pred['equipo_local']} vs {pred['equipo_visitante']}")
        print(f"  Fecha: {pred['fecha']} | Jornada: {pred['jornada']}")
        print(f"  Predicción: {pred['prediccion']} (Confianza: {pred['confianza']:.1f}%)")
        print(f"  Probabilidades:")
        print(f"    Victoria Local (1): {pred['probabilidades']['victoria_local']:.1f}%")
        print(f"    Empate (X):         {pred['probabilidades']['empate']:.1f}%")
        print(f"    Victoria Visit (2): {pred['probabilidades']['victoria_visitante']:.1f}%")
        print(f"  Factores clave:")
        print(f"    Local: Pos {pred['datos_equipos']['local']['posicion']} | "
              f"{pred['datos_equipos']['local']['puntos']} pts | "
              f"Forma {pred['datos_equipos']['local']['forma']:.1f}")
        print(f"    Visit: Pos {pred['datos_equipos']['visitante']['posicion']} | "
              f"{pred['datos_equipos']['visitante']['puntos']} pts | "
              f"Forma {pred['datos_equipos']['visitante']['forma']:.1f}")


def cargar_datos_liga(filename):
    """Carga los datos de una liga desde JSON"""
    filepath = DATA_DIR / filename
    
    if not filepath.exists():
        print(f"Advertencia: No se encontró {filename}")
        return None
    
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def analizar_equipos(clasificacion, liga_nombre):
    """Analiza estadísticas de equipos"""
    if not clasificacion:
        return {}
    
    # Top 5 equipos
    top_5 = clasificacion[:5]
    
    # Bottom 5 equipos
    bottom_5 = clasificacion[-5:]
    
    # Promedios generales
    total_equipos = len(clasificacion)
    promedio_puntos = sum(e['puntos'] for e in clasificacion) / total_equipos
    promedio_goles_favor = sum(e['goles_favor'] for e in clasificacion) / total_equipos
    promedio_goles_contra = sum(e['goles_contra'] for e in clasificacion) / total_equipos
    promedio_victorias = sum(e['porcentaje_victorias'] for e in clasificacion) / total_equipos
    
    # Mejor/peor ataque y defensa
    mejor_ataque = max(clasificacion, key=lambda x: x['goles_favor'])
    peor_ataque = min(clasificacion, key=lambda x: x['goles_favor'])
    mejor_defensa = min(clasificacion, key=lambda x: x['goles_contra'])
    peor_defensa = max(clasificacion, key=lambda x: x['goles_contra'])
    
    # Equipos con más victorias
    mas_victorias = max(clasificacion, key=lambda x: x['ganados'])
    mas_empates = max(clasificacion, key=lambda x: x['empatados'])
    mas_derrotas = max(clasificacion, key=lambda x: x['perdidos'])
    
    return {
        'liga': liga_nombre,
        'total_equipos': total_equipos,
        'top_5': [{'nombre': e['equipo'], 'puntos': e['puntos'], 'posicion': e['posicion']} for e in top_5],
        'bottom_5': [{'nombre': e['equipo'], 'puntos': e['puntos'], 'posicion': e['posicion']} for e in bottom_5],
        'promedios': {
            'puntos': round(promedio_puntos, 2),
            'goles_favor': round(promedio_goles_favor, 2),
            'goles_contra': round(promedio_goles_contra, 2),
            'porcentaje_victorias': round(promedio_victorias, 2)
        },
        'extremos': {
            'mejor_ataque': {
                'equipo': mejor_ataque['equipo'],
                'goles': mejor_ataque['goles_favor'],
                'promedio': mejor_ataque['promedio_goles_favor']
            },
            'peor_ataque': {
                'equipo': peor_ataque['equipo'],
                'goles': peor_ataque['goles_favor'],
                'promedio': peor_ataque['promedio_goles_favor']
            },
            'mejor_defensa': {
                'equipo': mejor_defensa['equipo'],
                'goles_contra': mejor_defensa['goles_contra'],
                'promedio': mejor_defensa['promedio_goles_contra']
            },
            'peor_defensa': {
                'equipo': peor_defensa['equipo'],
                'goles_contra': peor_defensa['goles_contra'],
                'promedio': peor_defensa['promedio_goles_contra']
            }
        },
        'records': {
            'mas_victorias': {
                'equipo': mas_victorias['equipo'],
                'victorias': mas_victorias['ganados'],
                'porcentaje': mas_victorias['porcentaje_victorias']
            },
            'mas_empates': {
                'equipo': mas_empates['equipo'],
                'empates': mas_empates['empatados']
            },
            'mas_derrotas': {
                'equipo': mas_derrotas['equipo'],
                'derrotas': mas_derrotas['perdidos']
            }
        }
    }


def comparar_ligas(analisis_primera, analisis_segunda):
    """Compara estadísticas entre Primera y Segunda División"""
    
    comparacion = {
        'fecha_analisis': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'comparacion': {
            'promedio_goles_favor': {
                'primera': analisis_primera['promedios']['goles_favor'],
                'segunda': analisis_segunda['promedios']['goles_favor'],
                'diferencia': round(analisis_primera['promedios']['goles_favor'] - analisis_segunda['promedios']['goles_favor'], 2)
            },
            'promedio_goles_contra': {
                'primera': analisis_primera['promedios']['goles_contra'],
                'segunda': analisis_segunda['promedios']['goles_contra'],
                'diferencia': round(analisis_primera['promedios']['goles_contra'] - analisis_segunda['promedios']['goles_contra'], 2)
            },
            'porcentaje_victorias': {
                'primera': analisis_primera['promedios']['porcentaje_victorias'],
                'segunda': analisis_segunda['promedios']['porcentaje_victorias'],
                'diferencia': round(analisis_primera['promedios']['porcentaje_victorias'] - analisis_segunda['promedios']['porcentaje_victorias'], 2)
            }
        },
        'conclusion': {
            'liga_mas_ofensiva': 'Primera' if analisis_primera['promedios']['goles_favor'] > analisis_segunda['promedios']['goles_favor'] else 'Segunda',
            'liga_mas_defensiva': 'Primera' if analisis_primera['promedios']['goles_contra'] < analisis_segunda['promedios']['goles_contra'] else 'Segunda',
            'liga_mas_competitiva': 'Primera' if analisis_primera['promedios']['porcentaje_victorias'] < analisis_segunda['promedios']['porcentaje_victorias'] else 'Segunda'
        }
    }
    
    return comparacion


def generar_reporte_consola(analisis_primera, analisis_segunda, comparacion):
    """Genera un reporte visual en consola"""
    
    print("\n" + "="*70)
    print("ANÁLISIS FÚTBOL ESPAÑOL 2025/26")
    print("="*70)
    
    # Primera División
    print("\n" + "-"*70)
    print("PRIMERA DIVISIÓN (LA LIGA)")
    print("-"*70)
    
    print("\nTOP 5:")
    for equipo in analisis_primera['top_5']:
        print(f"  {equipo['posicion']}. {equipo['nombre']:<30} {equipo['puntos']:>3} pts")
    
    print("\nPROMEDIOS GENERALES:")
    print(f"  Puntos por equipo: {analisis_primera['promedios']['puntos']}")
    print(f"  Goles favor: {analisis_primera['promedios']['goles_favor']}")
    print(f"  Goles contra: {analisis_primera['promedios']['goles_contra']}")
    print(f"  % Victorias: {analisis_primera['promedios']['porcentaje_victorias']}%")
    
    print("\nRECORDS:")
    print(f"  Mejor ataque: {analisis_primera['extremos']['mejor_ataque']['equipo']} ({analisis_primera['extremos']['mejor_ataque']['goles']} goles)")
    print(f"  Mejor defensa: {analisis_primera['extremos']['mejor_defensa']['equipo']} ({analisis_primera['extremos']['mejor_defensa']['goles_contra']} goles)")
    print(f"  Más victorias: {analisis_primera['records']['mas_victorias']['equipo']} ({analisis_primera['records']['mas_victorias']['victorias']} victorias, {analisis_primera['records']['mas_victorias']['porcentaje']}%)")
    
    # Segunda División
    print("\n" + "-"*70)
    print("SEGUNDA DIVISIÓN (LALIGA 2)")
    print("-"*70)
    
    print("\nTOP 5:")
    for equipo in analisis_segunda['top_5']:
        print(f"  {equipo['posicion']}. {equipo['nombre']:<30} {equipo['puntos']:>3} pts")
    
    print("\nPROMEDIOS GENERALES:")
    print(f"  Puntos por equipo: {analisis_segunda['promedios']['puntos']}")
    print(f"  Goles favor: {analisis_segunda['promedios']['goles_favor']}")
    print(f"  Goles contra: {analisis_segunda['promedios']['goles_contra']}")
    print(f"  % Victorias: {analisis_segunda['promedios']['porcentaje_victorias']}%")
    
    print("\nRECORDS:")
    print(f"  Mejor ataque: {analisis_segunda['extremos']['mejor_ataque']['equipo']} ({analisis_segunda['extremos']['mejor_ataque']['goles']} goles)")
    print(f"  Mejor defensa: {analisis_segunda['extremos']['mejor_defensa']['equipo']} ({analisis_segunda['extremos']['mejor_defensa']['goles_contra']} goles)")
    print(f"  Más victorias: {analisis_segunda['records']['mas_victorias']['equipo']} ({analisis_segunda['records']['mas_victorias']['victorias']} victorias, {analisis_segunda['records']['mas_victorias']['porcentaje']}%)")
    
    # Comparación
    print("\n" + "-"*70)
    print("COMPARACIÓN PRIMERA vs SEGUNDA")
    print("-"*70)
    
    comp = comparacion['comparacion']
    print(f"\nPromedio goles favor:")
    print(f"  Primera: {comp['promedio_goles_favor']['primera']}")
    print(f"  Segunda: {comp['promedio_goles_favor']['segunda']}")
    print(f"  Diferencia: {comp['promedio_goles_favor']['diferencia']}")
    
    print(f"\nPromedio goles contra:")
    print(f"  Primera: {comp['promedio_goles_contra']['primera']}")
    print(f"  Segunda: {comp['promedio_goles_contra']['segunda']}")
    print(f"  Diferencia: {comp['promedio_goles_contra']['diferencia']}")
    
    print(f"\n% Victorias promedio:")
    print(f"  Primera: {comp['porcentaje_victorias']['primera']}%")
    print(f"  Segunda: {comp['porcentaje_victorias']['segunda']}%")
    print(f"  Diferencia: {comp['porcentaje_victorias']['diferencia']}%")
    
    print("\nCONCLUSIONES:")
    print(f"  Liga más ofensiva: {comparacion['conclusion']['liga_mas_ofensiva']}")
    print(f"  Liga más defensiva: {comparacion['conclusion']['liga_mas_defensiva']}")
    print(f"  Liga más competitiva: {comparacion['conclusion']['liga_mas_competitiva']}")
    
    print("\n" + "="*70)


def main():
    print("="*70)
    print("SCRAPPER FÚTBOL ESPAÑOL - PRIMERA Y SEGUNDA DIVISIÓN")
    print("="*70)
    
    # 1. Ejecutar scrapper de Primera División
    resultado_primera = ejecutar_script(
        'scrapper-soccerdata.py',
        'Primera División (La Liga)'
    )
    
    # 2. Ejecutar scrapper de Segunda División
    resultado_segunda = ejecutar_script(
        'scrapper-segunda-division.py',
        'Segunda División (LaLiga 2)'
    )
    
    if not resultado_primera or not resultado_segunda:
        print("\n✗ Error: No se pudieron obtener todos los datos")
        return
    
    print("\n" + "="*70)
    print("ANALIZANDO DATOS")
    print("="*70)
    
    # 3. Cargar datos
    datos_primera = cargar_datos_liga('esp_la_liga_resultados.json')
    datos_segunda = cargar_datos_liga('segunda_division_completo.json')
    
    if not datos_primera or not datos_segunda:
        print("\n✗ Error: No se pudieron cargar los datos")
        return
    
    # 4. Analizar cada liga
    analisis_primera = analizar_equipos(
        datos_primera.get('clasificacion', []),
        'Primera División'
    )
    
    analisis_segunda = analizar_equipos(
        datos_segunda.get('clasificacion', []),
        'Segunda División'
    )
    
    # 5. Comparar ligas
    comparacion = comparar_ligas(analisis_primera, analisis_segunda)
    
    # 6. Generar predicciones para próximos partidos
    print("\n" + "="*70)
    print("GENERANDO PREDICCIONES")
    print("="*70)
    
    predicciones_primera = predecir_proximos_partidos(datos_primera, 'Primera División')
    predicciones_segunda = predecir_proximos_partidos(datos_segunda, 'Segunda División')
    
    print(f"\n✓ Generadas {len(predicciones_primera)} predicciones para Primera División")
    print(f"✓ Generadas {len(predicciones_segunda)} predicciones para Segunda División")
    
    # 7. Generar análisis completo
    analisis_completo = {
        'fecha_analisis': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'temporada': '2025/26',
        'primera_division': analisis_primera,
        'segunda_division': analisis_segunda,
        'comparacion': comparacion,
        'predicciones': {
            'primera_division': predicciones_primera,
            'segunda_division': predicciones_segunda,
            'total_predicciones': len(predicciones_primera) + len(predicciones_segunda)
        },
        'metodologia': {
            'descripcion': 'Predicciones basadas en análisis multifactorial',
            'factores': [
                'Posición en tabla',
                'Diferencia de puntos',
                'Forma reciente (últimos 5 partidos)',
                'Ratio de goles favor/contra',
                'Ventaja de local',
                'Porcentaje de victorias'
            ],
            'nota': 'Las predicciones deben verificarse contra resultados reales para análisis de precisión'
        }
    }
    
    # 8. Guardar análisis
    output_path = DATA_DIR / 'analisis_futbol_espanol.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(analisis_completo, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ Análisis guardado en: {output_path}")
    
    # 9. Guardar predicciones por separado para seguimiento
    predicciones_path = DATA_DIR / 'predicciones_proxima_jornada.json'
    predicciones_seguimiento = {
        'fecha_prediccion': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'temporada': '2025/26',
        'predicciones': predicciones_primera + predicciones_segunda,
        'total': len(predicciones_primera) + len(predicciones_segunda),
        'por_verificar': len(predicciones_primera) + len(predicciones_segunda),
        'verificadas': 0
    }
    print(f"  - {DATA_DIR / 'predicciones_proxima_jornada.json'}")
    
    print(f"\nPRÓXIMOS PASOS PARA BIG DATA:")
    print(f"  1. Ejecutar este script antes de cada jornada para generar predicciones")
    print(f"  2. Después de los partidos, volver a ejecutar para obtener resultados reales")
    print(f"  3. Comparar predicciones vs resultados reales")
    print(f"  4. Acumular datos históricos para mejorar el modelo predictivo")
    print(f"  5. Analizar: % aciertos, qué factores son más relevantes, ajustar pesos")
    
    with open(predicciones_path, 'w', encoding='utf-8') as f:
        json.dump(predicciones_seguimiento, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Predicciones guardadas en: {predicciones_path}")
    
    # 10. Mostrar reporte en consola
    generar_reporte_consola(analisis_primera, analisis_segunda, comparacion)
    
    # 11. Mostrar predicciones
    generar_reporte_predicciones(predicciones_primera, 'Primera División')
    generar_reporte_predicciones(predicciones_segunda, 'Segunda División')
    
    print("\n" + "="*70)
    print("PROCESO COMPLETADO")
    print("="*70)
    print(f"\nARCHIVOS GENERADOS:")
    print(f"  - {DATA_DIR / 'esp_la_liga_resultados.json'}")
    print(f"  - {DATA_DIR / 'segunda_division_completo.json'}")
    print(f"  - {DATA_DIR / 'analisis_futbol_espanol.json'}")


if __name__ == "__main__":
    main()
