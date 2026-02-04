#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para analizar la quiniela basándose en las predicciones del análisis de fútbol español
"""

import json
import re
from pathlib import Path
from bs4 import BeautifulSoup
from datetime import datetime
import unicodedata

def normalizar_nombre_equipo(nombre):
    """Normaliza el nombre del equipo para hacer matching"""
    # Eliminar acentos y convertir a mayúsculas
    nombre = unicodedata.normalize('NFD', nombre.upper())
    nombre = ''.join(char for char in nombre if unicodedata.category(char) != 'Mn')
    
    # Eliminar puntos y normalizar espacios
    nombre = nombre.replace('.', ' ').strip()
    nombre = ' '.join(nombre.split())  # Normalizar espacios múltiples
    
    # Diccionario de mapeos comunes (después de normalización)
    mapeos = {
        'BCN': 'BARCELONA',
        'BARCA': 'BARCELONA',
        'BARCELONA': 'BARCELONA',
        'R MADRID': 'MADRID',
        'REAL M': 'MADRID',
        'REAL MADRID': 'MADRID',
        'MADRID': 'MADRID',
        'RMADRID': 'MADRID',
        'ATL MADRID': 'ATLETICO',
        'AT MADRID': 'ATLETICO',
        'ATLETICO MADRID': 'ATLETICO',
        'ATLETICO': 'ATLETICO',
        'ATMADR': 'ATLETICO',
        'ATH CLUB': 'ATHLETIC',
        'ATHLETIC CLUB': 'ATHLETIC',
        'ATHLETIC': 'ATHLETIC',
        'R SOCIEDAD': 'SOCIEDAD',
        'RSOCIEDAD': 'SOCIEDAD',
        'REAL SOCIEDAD': 'SOCIEDAD',
        'R BETIS': 'BETIS',
        'REAL BETIS': 'BETIS',
        'BETIS': 'BETIS',
        'VILLARREAL': 'VILLARREAL',
        'VILLA': 'VILLARREAL',
        'SEVILLA': 'SEVILLA',
        'VALENCIA': 'VALENCIA',
        'CELTA': 'CELTA',
        'CELTA VIGO': 'CELTA',
        'ESPANYOL': 'ESPANYOL',
        'GETAFE': 'GETAFE',
        'GRANADA': 'GRANADA',
        'OSASUNA': 'OSASUNA',
        'VALLADOLID': 'VALLADOLID',
        'R VALLADOLID': 'VALLADOLID',
        'REAL VALLADOLID': 'VALLADOLID',
        'ALAVES': 'ALAVES',
        'ALAV': 'ALAVES',
        'DEPORTIVO ALAVES': 'ALAVES',
        'MALLORCA': 'MALLORCA',
        'MALL': 'MALLORCA',
        'CADIZ': 'CADIZ',
        'ELCHE': 'ELCHE',
        'ALMERIA': 'ALMERIA',
        'GIRONA': 'GIRONA',
        'GIR': 'GIRONA',
        'GIRONA FC': 'GIRONA',
        'RAYO': 'RAYO',
        'R VALLECANO': 'RAYO',
        'RAYO VALLECANO': 'RAYO',
        'LAS PALMAS': 'PALMAS',
        'PALMAS': 'PALMAS',
        'LEVANTE': 'LEVANTE',
        'LEVANTE UD': 'LEVANTE',
        'OVIEDO': 'OVIEDO',
        'R OVIEDO': 'OVIEDO',
        'REAL OVIEDO': 'OVIEDO',
        'OVIE': 'OVIEDO',
        'SPORTING': 'SPORTING',
        'SPORTING GIJON': 'SPORTING',
        'GIJON': 'SPORTING',
        'LEGANES': 'LEGANES',
        'LEGAN': 'LEGANES',
        'EIBAR': 'EIBAR',
        'TENERIFE': 'TENERIFE',
        'ZARAGOZA': 'ZARAGOZA',
        'R ZARAGOZA': 'ZARAGOZA',
        'REAL ZARAGOZA': 'ZARAGOZA',
        'MIRANDES': 'MIRANDES',
        'MIRA': 'MIRANDES',
        'RACING': 'RACING',
        'R RACING': 'RACING',
        'REAL RACING CLUB': 'RACING',
        'CASTELLON': 'CASTELLON',
        'CAST': 'CASTELLON',
        'CD CASTELLON': 'CASTELLON',
        'DEPORTIVO': 'DEPORTIVO',
        'DEPOR': 'DEPORTIVO',
        'DEPORTIVO LA CORUNA': 'DEPORTIVO',
        'CORDOBA': 'CORDOBA',
        'CORD': 'CORDOBA',
        'HUESCA': 'HUESCA',
        'BURGOS': 'BURGOS',
        'BURG': 'BURGOS',
        'BURGOS CLUB DE FUTBOL': 'BURGOS',
        'ANDORRA': 'ANDORRA',
        'AND': 'ANDORRA',
        'FC ANDORRA': 'ANDORRA',
        'ALBACETE': 'ALBACETE',
        'ALBA': 'ALBACETE',
        'ALBACETE BALOMPIE': 'ALBACETE',
        'CEUTA': 'CEUTA',
        'AD CEUTA': 'CEUTA',
        'MALAGA': 'MALAGA',
        'MALA': 'MALAGA',
        'LEONESA': 'LEONESA',
        'C LEONESA': 'LEONESA',
        'CULTURAL LEONESA': 'LEONESA'
    }
    
    # Buscar en mapeos (coincidencia exacta primero)
    if nombre in mapeos:
        return mapeos[nombre]
    
    # Buscar coincidencia parcial
    for clave, valor in mapeos.items():
        if clave in nombre or nombre in clave:
            return valor
    
    return nombre


def extraer_partidos_quiniela(html_path):
    """Extrae los partidos del HTML de la quiniela"""
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()
    
    soup = BeautifulSoup(html, 'html.parser')
    partidos = []
    
    # Buscar todos los partidos
    partidos_divs = soup.find_all('div', class_='c-caja_base__partido')
    
    for partido_div in partidos_divs:
        try:
            # Número del partido
            numero_elem = partido_div.find('span', class_='c-equipos__number')
            if not numero_elem:
                continue
            numero = numero_elem.text.strip()
            
            # Equipos
            equipos_elem = partido_div.find('span', class_='c-equipos__teams')
            if not equipos_elem:
                continue
            
            # Extraer del atributo aria-label
            aria_label = equipos_elem.get('aria-label', '')
            if ' contra ' in aria_label:
                partes = aria_label.split(' contra ')
                equipo_local = partes[0].strip()
                equipo_visitante = partes[1].strip()
            else:
                # Extraer del data-short
                data_short = equipos_elem.get('data-short', '')
                if ' - ' in data_short:
                    partes = data_short.split(' - ')
                    equipo_local = partes[0].strip()
                    equipo_visitante = partes[1].strip()
                else:
                    continue
            
            # Hora del partido
            horario_elem = partido_div.find('div', class_='c-marcador-horario__time')
            horario = horario_elem.text.strip() if horario_elem else 'Hora no disponible'
            
            partidos.append({
                'numero': numero,
                'equipo_local': equipo_local,
                'equipo_visitante': equipo_visitante,
                'equipo_local_normalizado': normalizar_nombre_equipo(equipo_local),
                'equipo_visitante_normalizado': normalizar_nombre_equipo(equipo_visitante),
                'horario': horario
            })
        except Exception as e:
            print(f"Error procesando partido: {e}")
            continue
    
    return partidos


def encontrar_prediccion(partido_quiniela, predicciones):
    """Encuentra la predicción correspondiente a un partido de la quiniela"""
    local_norm = partido_quiniela['equipo_local_normalizado']
    visitante_norm = partido_quiniela['equipo_visitante_normalizado']
    
    for pred in predicciones:
        pred_local = normalizar_nombre_equipo(pred['equipo_local'])
        pred_visitante = normalizar_nombre_equipo(pred['equipo_visitante'])
        
        # Match exacto
        if pred_local == local_norm and pred_visitante == visitante_norm:
            return pred
        
        # Match parcial (contiene)
        if local_norm in pred_local or pred_local in local_norm:
            if visitante_norm in pred_visitante or pred_visitante in visitante_norm:
                return pred
    
    return None


def calcular_apuesta_goles(prediccion):
    """Calcula la apuesta de goles totales (0, 1, 2 o M) basándose en las estadísticas"""
    # Obtener promedios de goles
    goles_local = prediccion['datos_equipos']['local']['goles_favor']
    goles_visitante = prediccion['datos_equipos']['visitante']['goles_favor']
    
    # Estimar goles totales esperados
    goles_esperados = goles_local + goles_visitante
    
    # Calcular probabilidades basadas en distribución de Poisson simplificada
    # y los promedios de goles
    if goles_esperados < 1.0:
        probs = {'0': 40.0, '1': 35.0, '2': 15.0, 'M': 10.0}
    elif goles_esperados < 1.5:
        probs = {'0': 25.0, '1': 35.0, '2': 25.0, 'M': 15.0}
    elif goles_esperados < 2.0:
        probs = {'0': 15.0, '1': 30.0, '2': 30.0, 'M': 25.0}
    elif goles_esperados < 2.5:
        probs = {'0': 10.0, '1': 25.0, '2': 30.0, 'M': 35.0}
    elif goles_esperados < 3.0:
        probs = {'0': 5.0, '1': 20.0, '2': 30.0, 'M': 45.0}
    else:  # >= 3.0
        probs = {'0': 3.0, '1': 12.0, '2': 25.0, 'M': 60.0}
    
    # Determinar la apuesta recomendada (mayor probabilidad)
    apuesta_recomendada = max(probs, key=probs.get)
    confianza = probs[apuesta_recomendada]
    
    return {
        'apuesta': apuesta_recomendada,
        'confianza': confianza,
        'probabilidades': probs,
        'goles_esperados': round(goles_esperados, 2)
    }


def generar_apuestas_quiniela(partidos_quiniela, predicciones_primera, predicciones_segunda):
    """Genera las apuestas recomendadas para la quiniela"""
    todas_predicciones = predicciones_primera + predicciones_segunda
    apuestas = []
    
    for partido in partidos_quiniela:
        prediccion = encontrar_prediccion(partido, todas_predicciones)
        
        # Partido 15: Apuesta especial de goles (0, 1, 2, M)
        if partido['numero'] == '15' and prediccion:
            resultado_goles = calcular_apuesta_goles(prediccion)
            
            apuesta = {
                'numero': partido['numero'],
                'equipo_local': partido['equipo_local'],
                'equipo_visitante': partido['equipo_visitante'],
                'horario': partido['horario'],
                'apuesta_recomendada': resultado_goles['apuesta'],
                'confianza': round(resultado_goles['confianza'], 2),
                'probabilidades': resultado_goles['probabilidades'],
                'liga': prediccion.get('liga', 'Desconocida'),
                'fecha_partido': prediccion.get('fecha', 'N/A'),
                'tipo_apuesta': 'GOLES',
                'goles_esperados': resultado_goles['goles_esperados'],
                # Información adicional sobre quién gana
                'prediccion_ganador': prediccion['prediccion'],
                'confianza_ganador': round(prediccion['confianza'], 2),
                'probabilidades_1x2': {
                    '1': round(prediccion['probabilidades']['victoria_local'], 2),
                    'X': round(prediccion['probabilidades']['empate'], 2),
                    '2': round(prediccion['probabilidades']['victoria_visitante'], 2)
                }
            }
            
            # Determinar nivel de confianza
            if apuesta['confianza'] >= 45:
                apuesta['nivel_confianza'] = 'ALTA'
            elif apuesta['confianza'] >= 35:
                apuesta['nivel_confianza'] = 'MEDIA'
            else:
                apuesta['nivel_confianza'] = 'BAJA'
            
            apuestas.append(apuesta)
        
        elif prediccion:
            apuesta = {
                'numero': partido['numero'],
                'equipo_local': partido['equipo_local'],
                'equipo_visitante': partido['equipo_visitante'],
                'horario': partido['horario'],
                'apuesta_recomendada': prediccion['prediccion'],
                'confianza': round(prediccion['confianza'], 2),
                'probabilidades': {
                    '1': round(prediccion['probabilidades']['victoria_local'], 2),
                    'X': round(prediccion['probabilidades']['empate'], 2),
                    '2': round(prediccion['probabilidades']['victoria_visitante'], 2)
                },
                'liga': prediccion.get('liga', 'Desconocida'),
                'fecha_partido': prediccion.get('fecha', 'N/A'),
                'tipo_apuesta': '1X2'
            }
            
            # Determinar nivel de confianza
            if apuesta['confianza'] >= 70:
                apuesta['nivel_confianza'] = 'ALTA'
            elif apuesta['confianza'] >= 55:
                apuesta['nivel_confianza'] = 'MEDIA'
            else:
                apuesta['nivel_confianza'] = 'BAJA'
            
            apuestas.append(apuesta)
        else:
            # No se encontró predicción
            if partido['numero'] == '15':
                # Partido 15 sin predicción
                apuestas.append({
                    'numero': partido['numero'],
                    'equipo_local': partido['equipo_local'],
                    'equipo_visitante': partido['equipo_visitante'],
                    'horario': partido['horario'],
                    'apuesta_recomendada': 'M',  # Por defecto más de 2 goles
                    'confianza': 0,
                    'probabilidades': {
                        '0': 25.0,
                        '1': 25.0,
                        '2': 25.0,
                        'M': 25.0
                    },
                    'liga': 'No encontrada',
                    'fecha_partido': 'N/A',
                    'nivel_confianza': 'SIN DATOS',
                    'tipo_apuesta': 'GOLES',
                    'nota': 'No se encontró predicción para este partido'
                })
            else:
                apuestas.append({
                    'numero': partido['numero'],
                    'equipo_local': partido['equipo_local'],
                    'equipo_visitante': partido['equipo_visitante'],
                    'horario': partido['horario'],
                    'apuesta_recomendada': 'X',  # Por defecto empate si no hay predicción
                    'confianza': 0,
                    'probabilidades': {
                        '1': 33.33,
                        'X': 33.33,
                        '2': 33.33
                    },
                    'liga': 'No encontrada',
                    'fecha_partido': 'N/A',
                    'nivel_confianza': 'SIN DATOS',
                    'tipo_apuesta': '1X2',
                    'nota': 'No se encontró predicción para este partido'
                })
    
    return apuestas


def imprimir_boleto_quiniela(apuestas):
    """Imprime el boleto de quiniela con formato bonito"""
    print("\n" + "="*80)
    print("BOLETO QUINIELA - PREDICCIONES BASADAS EN ANÁLISIS")
    print(f"Fecha de análisis: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("="*80)
    
    for apuesta in apuestas:
        tipo_apuesta = apuesta.get('tipo_apuesta', '1X2')
        
        if tipo_apuesta == 'GOLES':
            # Partido 15: apuesta de goles
            simbolo_apuesta = apuesta['apuesta_recomendada']
            
            # Color según confianza
            confianza_str = f"{apuesta['confianza']}%"
            if apuesta['nivel_confianza'] == 'ALTA':
                confianza_display = f"[OK] {confianza_str}"
            elif apuesta['nivel_confianza'] == 'MEDIA':
                confianza_display = f"~ {confianza_str}"
            elif apuesta['nivel_confianza'] == 'BAJA':
                confianza_display = f"? {confianza_str}"
            else:
                confianza_display = f"[NO] {confianza_str}"
            
            print(f"\n{apuesta['numero']:>2}. {apuesta['equipo_local']} vs {apuesta['equipo_visitante']}")
            print(f"    Horario: {apuesta['horario']} | Liga: {apuesta['liga']}")
            print(f"    APUESTA: [{simbolo_apuesta}] {confianza_display} ({apuesta['nivel_confianza']}) [PARTIDO DE GOLES]")
            if 'goles_esperados' in apuesta:
                print(f"    Goles esperados: {apuesta['goles_esperados']}")
            print(f"    Probabilidades -> 0: {apuesta['probabilidades']['0']}% | 1: {apuesta['probabilidades']['1']}% | 2: {apuesta['probabilidades']['2']}% | M: {apuesta['probabilidades']['M']}%")
            # Mostrar también quién gana
            if 'prediccion_ganador' in apuesta:
                simbolo_ganador = {'V': '1', 'E': 'X', 'D': '2'}.get(apuesta['prediccion_ganador'], apuesta['prediccion_ganador'])
                print(f"    GANADOR PROBABLE: [{simbolo_ganador}] {apuesta['confianza_ganador']}%")
                print(f"    Probabilidades 1X2 -> 1: {apuesta['probabilidades_1x2']['1']}% | X: {apuesta['probabilidades_1x2']['X']}% | 2: {apuesta['probabilidades_1x2']['2']}%")
        else:
            # Partido normal 1X2
            simbolo_apuesta = {
                'V': '1',
                'E': 'X',
                'D': '2'
            }.get(apuesta['apuesta_recomendada'], apuesta['apuesta_recomendada'])
            
            # Color según confianza
            confianza_str = f"{apuesta['confianza']}%"
            if apuesta['nivel_confianza'] == 'ALTA':
                confianza_display = f"[OK] {confianza_str}"
            elif apuesta['nivel_confianza'] == 'MEDIA':
                confianza_display = f"~ {confianza_str}"
            elif apuesta['nivel_confianza'] == 'BAJA':
                confianza_display = f"? {confianza_str}"
            else:
                confianza_display = f"[NO] {confianza_str}"
            
            print(f"\n{apuesta['numero']:>2}. {apuesta['equipo_local']} vs {apuesta['equipo_visitante']}")
            print(f"    Horario: {apuesta['horario']} | Liga: {apuesta['liga']}")
            print(f"    APUESTA: [{simbolo_apuesta}] {confianza_display} ({apuesta['nivel_confianza']})")
            print(f"    Probabilidades -> 1: {apuesta['probabilidades']['1']}% | X: {apuesta['probabilidades']['X']}% | 2: {apuesta['probabilidades']['2']}%")
        
        if 'nota' in apuesta:
            print(f"    NOTA: {apuesta['nota']}")
    
    print("\n" + "="*80)
    print("RESUMEN DE APUESTAS")
    print("="*80)
    
    # Contar apuestas por tipo
    apuestas_1 = sum(1 for a in apuestas if a['apuesta_recomendada'] in ['V', '1'])
    apuestas_x = sum(1 for a in apuestas if a['apuesta_recomendada'] in ['E', 'X'])
    apuestas_2 = sum(1 for a in apuestas if a['apuesta_recomendada'] in ['D', '2'])
    
    print(f"Total de partidos: {len(apuestas)}")
    print(f"Apuestas al 1 (Local): {apuestas_1}")
    print(f"Apuestas al X (Empate): {apuestas_x}")
    print(f"Apuestas al 2 (Visitante): {apuestas_2}")
    
    # Contar por nivel de confianza
    alta = sum(1 for a in apuestas if a['nivel_confianza'] == 'ALTA')
    media = sum(1 for a in apuestas if a['nivel_confianza'] == 'MEDIA')
    baja = sum(1 for a in apuestas if a['nivel_confianza'] == 'BAJA')
    sin_datos = sum(1 for a in apuestas if a['nivel_confianza'] == 'SIN DATOS')
    
    print(f"\nNivel de confianza:")
    print(f"  Alta (>=70%): {alta} partidos")
    print(f"  Media (55-69%): {media} partidos")
    print(f"  Baja (<55%): {baja} partidos")
    print(f"  Sin datos: {sin_datos} partidos")
    
    print("="*80)


def main():
    """Función principal"""
    # Rutas
    base_dir = Path(__file__).parent.parent
    data_dir = base_dir / 'data'
    
    analisis_path = data_dir / 'analisis_futbol_espanol.json'
    html_path = data_dir / 'Jornada_quiniela.html'
    output_path = data_dir / 'apuestas_quiniela.json'
    
    # Verificar que existen los archivos
    if not analisis_path.exists():
        print(f"Error: No se encuentra el archivo {analisis_path}")
        print("Ejecuta primero: python scrapper-futbol-espanol.py")
        return
    
    if not html_path.exists():
        print(f"Error: No se encuentra el archivo {html_path}")
        return
    
    print("Cargando análisis de fútbol español...")
    with open(analisis_path, 'r', encoding='utf-8') as f:
        analisis = json.load(f)
    
    predicciones_primera = analisis['predicciones']['primera_division']
    predicciones_segunda = analisis['predicciones']['segunda_division']
    
    print(f"[OK] Cargadas {len(predicciones_primera)} predicciones de Primera División")
    print(f"[OK] Cargadas {len(predicciones_segunda)} predicciones de Segunda División")
    
    print("\nExtrayendo partidos del HTML de la quiniela...")
    partidos_quiniela = extraer_partidos_quiniela(html_path)
    print(f"[OK] Extraídos {len(partidos_quiniela)} partidos de la quiniela")
    
    print("\nGenerando apuestas recomendadas...")
    apuestas = generar_apuestas_quiniela(partidos_quiniela, predicciones_primera, predicciones_segunda)
    
    # Guardar apuestas en JSON
    resultado = {
        'fecha_analisis': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'total_partidos': len(apuestas),
        'apuestas': apuestas,
        'estadisticas': {
            'apuestas_1': sum(1 for a in apuestas if a['apuesta_recomendada'] in ['V', '1']),
            'apuestas_x': sum(1 for a in apuestas if a['apuesta_recomendada'] in ['E', 'X']),
            'apuestas_2': sum(1 for a in apuestas if a['apuesta_recomendada'] in ['D', '2']),
            'confianza_alta': sum(1 for a in apuestas if a['nivel_confianza'] == 'ALTA'),
            'confianza_media': sum(1 for a in apuestas if a['nivel_confianza'] == 'MEDIA'),
            'confianza_baja': sum(1 for a in apuestas if a['nivel_confianza'] == 'BAJA'),
            'sin_datos': sum(1 for a in apuestas if a['nivel_confianza'] == 'SIN DATOS')
        }
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)
    
    print(f"\n[OK] Apuestas guardadas en: {output_path}")
    
    # Imprimir boleto
    imprimir_boleto_quiniela(apuestas)


if __name__ == '__main__':
    main()
