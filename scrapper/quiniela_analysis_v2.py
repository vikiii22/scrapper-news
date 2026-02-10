#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script MEJORADO para analizar la quiniela con factores avanzados
Incluye:
- Estadísticas local/visitante diferenciadas
- Head-to-head (enfrentamientos directos)
- Climatología (si hay API key configurada)
- Racha de resultados recientes
- Días de descanso entre partidos
- Importancia del partido (descenso, título, Europa, etc.)
"""

import json
import re
from pathlib import Path
from bs4 import BeautifulSoup
from datetime import datetime
import unicodedata
import sys

# Importar el módulo de factores avanzados
from advanced_factors import FactoresAvanzados


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


def ajustar_probabilidades_con_factores(
    probabilidades: dict,
    factores_avanzados: dict,
    peso_factores: float = 0.3
) -> dict:
    """
    Ajusta las probabilidades base con los factores avanzados calculados
    
    Args:
        probabilidades: dict con victoria_local, empate, victoria_visitante
        factores_avanzados: resultado de FactoresAvanzados.calcular_todos_factores()
        peso_factores: qué tanto peso dar a los factores (0-1)
    
    Returns:
        dict con probabilidades ajustadas
    """
    factor_total = factores_avanzados.get('factor_total', 0)
    
    # Convertir factor a ajuste de probabilidad
    # Factor positivo = favorece al local
    # Factor negativo = favorece al visitante
    ajuste = factor_total * peso_factores
    
    # Obtener probabilidades originales
    prob_local = probabilidades.get('victoria_local', 33.33)
    prob_empate = probabilidades.get('empate', 33.33)
    prob_visitante = probabilidades.get('victoria_visitante', 33.33)
    
    # Aplicar ajuste
    prob_local_ajustada = prob_local + ajuste
    prob_visitante_ajustada = prob_visitante - ajuste
    
    # Pequeño ajuste al empate si hay mucha diferencia
    if abs(ajuste) > 5:
        prob_empate -= abs(ajuste) * 0.2
    
    # Normalizar para que sume 100%
    total = prob_local_ajustada + prob_empate + prob_visitante_ajustada
    
    # Asegurar que no hay negativos
    prob_local_ajustada = max(5, prob_local_ajustada)
    prob_empate = max(5, prob_empate)
    prob_visitante_ajustada = max(5, prob_visitante_ajustada)
    
    total = prob_local_ajustada + prob_empate + prob_visitante_ajustada
    
    return {
        'victoria_local': round((prob_local_ajustada / total) * 100, 2),
        'empate': round((prob_empate / total) * 100, 2),
        'victoria_visitante': round((prob_visitante_ajustada / total) * 100, 2)
    }


def calcular_apuesta_goles_mejorado(prediccion, factores_avanzados=None):
    """
    Calcula la apuesta de goles totales (0, 1, 2 o M) 
    basándose en las estadísticas y factores avanzados
    """
    # Obtener promedios de goles
    goles_local = prediccion['datos_equipos']['local']['goles_favor']
    goles_visitante = prediccion['datos_equipos']['visitante']['goles_favor']
    
    # Estimar goles totales esperados
    goles_esperados = goles_local + goles_visitante
    
    # Ajustar por clima (si llueve, menos goles típicamente)
    if factores_avanzados:
        clima = factores_avanzados.get('factores', {}).get('clima', {})
        if clima.get('clima_disponible'):
            clima_info = clima.get('clima', {})
            # Lluvia reduce goles
            if clima_info.get('lluvia', 0) > 0 or clima_info.get('nieve', 0) > 0:
                goles_esperados *= 0.85
            # Viento fuerte reduce goles
            if clima_info.get('viento_velocidad', 0) > 11:
                goles_esperados *= 0.90
        
        # Ajustar por importancia (partidos importantes = menos goles)
        importancia_local = factores_avanzados.get('factores', {}).get('importancia', {})
        if importancia_local.get('importancia_local', {}).get('importancia') == 'muy_alta':
            goles_esperados *= 0.95  # Más conservador
    
    # Calcular probabilidades basadas en distribución de Poisson simplificada
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


def generar_apuestas_quiniela_mejorado(
    partidos_quiniela, 
    predicciones_primera, 
    predicciones_segunda,
    datos_completos_primera,
    datos_completos_segunda,
    usar_factores_avanzados=True
):
    """
    Genera las apuestas recomendadas para la quiniela
    con factores avanzados integrados
    """
    todas_predicciones = predicciones_primera + predicciones_segunda
    apuestas = []
    
    # Inicializar módulo de factores avanzados
    fa = FactoresAvanzados() if usar_factores_avanzados else None
    
    for partido in partidos_quiniela:
        prediccion = encontrar_prediccion(partido, todas_predicciones)
        
        # Determinar qué datos usar según la liga
        es_primera = prediccion.get('liga', '').lower().find('primera') >= 0 if prediccion else False
        datos_liga = datos_completos_primera if es_primera else datos_completos_segunda
        partidos_jugados = datos_liga.get('todos_partidos_jugados', [])
        clasificacion = datos_liga.get('clasificacion', [])
        
        # Calcular factores avanzados si están habilitados
        factores_avanzados = None
        if fa and prediccion:
            try:
                factores_avanzados = fa.calcular_todos_factores(
                    equipo_local=prediccion['equipo_local'],
                    equipo_local_norm=partido['equipo_local_normalizado'],
                    equipo_visitante=prediccion['equipo_visitante'],
                    equipo_visitante_norm=partido['equipo_visitante_normalizado'],
                    partidos_jugados=partidos_jugados,
                    clasificacion=clasificacion,
                    fecha_partido=prediccion.get('fecha')
                )
            except Exception as e:
                print(f"  Aviso: No se pudieron calcular factores avanzados para partido {partido['numero']}: {e}")
        
        # Partido 15: Apuesta especial de goles (0, 1, 2, M)
        if partido['numero'] == '15' and prediccion:
            resultado_goles = calcular_apuesta_goles_mejorado(prediccion, factores_avanzados)
            
            # Ajustar probabilidades del resultado con factores
            probs_ajustadas = prediccion['probabilidades'].copy()
            if factores_avanzados:
                probs_ajustadas = ajustar_probabilidades_con_factores(
                    prediccion['probabilidades'],
                    factores_avanzados
                )
            
            # Determinar predicción de ganador con prob ajustadas
            max_prob = max(probs_ajustadas['victoria_local'], probs_ajustadas['empate'], probs_ajustadas['victoria_visitante'])
            if max_prob == probs_ajustadas['victoria_local']:
                prediccion_ganador = 'V'
                confianza_ganador = probs_ajustadas['victoria_local']
            elif max_prob == probs_ajustadas['empate']:
                prediccion_ganador = 'E'
                confianza_ganador = probs_ajustadas['empate']
            else:
                prediccion_ganador = 'D'
                confianza_ganador = probs_ajustadas['victoria_visitante']
            
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
                'prediccion_ganador': prediccion_ganador,
                'confianza_ganador': round(confianza_ganador, 2),
                'probabilidades_1x2': {
                    '1': round(probs_ajustadas['victoria_local'], 2),
                    'X': round(probs_ajustadas['empate'], 2),
                    '2': round(probs_ajustadas['victoria_visitante'], 2)
                },
                'factores_avanzados': factores_avanzados.get('resumen') if factores_avanzados else None
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
            # Ajustar probabilidades con factores avanzados
            probs_originales = prediccion['probabilidades']
            if factores_avanzados:
                probs_ajustadas = ajustar_probabilidades_con_factores(
                    probs_originales,
                    factores_avanzados
                )
            else:
                probs_ajustadas = {
                    'victoria_local': probs_originales['victoria_local'],
                    'empate': probs_originales['empate'],
                    'victoria_visitante': probs_originales['victoria_visitante']
                }
            
            # Determinar predicción basada en probabilidades ajustadas
            max_prob = max(probs_ajustadas['victoria_local'], probs_ajustadas['empate'], probs_ajustadas['victoria_visitante'])
            if max_prob == probs_ajustadas['victoria_local']:
                prediccion_final = 'V'
                confianza = probs_ajustadas['victoria_local']
            elif max_prob == probs_ajustadas['empate']:
                prediccion_final = 'E'
                confianza = probs_ajustadas['empate']
            else:
                prediccion_final = 'D'
                confianza = probs_ajustadas['victoria_visitante']
            
            apuesta = {
                'numero': partido['numero'],
                'equipo_local': partido['equipo_local'],
                'equipo_visitante': partido['equipo_visitante'],
                'horario': partido['horario'],
                'apuesta_recomendada': prediccion_final,
                'apuesta_original': prediccion['prediccion'],  # Para comparar
                'confianza': round(confianza, 2),
                'confianza_original': round(prediccion['confianza'], 2),
                'probabilidades': {
                    '1': round(probs_ajustadas['victoria_local'], 2),
                    'X': round(probs_ajustadas['empate'], 2),
                    '2': round(probs_ajustadas['victoria_visitante'], 2)
                },
                'probabilidades_originales': {
                    '1': round(probs_originales['victoria_local'], 2),
                    'X': round(probs_originales['empate'], 2),
                    '2': round(probs_originales['victoria_visitante'], 2)
                },
                'liga': prediccion.get('liga', 'Desconocida'),
                'fecha_partido': prediccion.get('fecha', 'N/A'),
                'tipo_apuesta': '1X2',
                'factores_avanzados': factores_avanzados.get('resumen') if factores_avanzados else None
            }
            
            # Añadir información de factores destacados
            if factores_avanzados:
                resumen = factores_avanzados.get('resumen', {})
                factores_destacados = []
                
                if abs(resumen.get('h2h', 0)) >= 1.5:
                    factores_destacados.append(f"H2H: {'Favorece local' if resumen['h2h'] > 0 else 'Favorece visitante'}")
                
                if resumen.get('localidad', 0) >= 8:
                    factores_destacados.append("Local muy fuerte en casa")
                elif resumen.get('localidad', 0) <= 3:
                    factores_destacados.append("Local débil en casa")
                
                if abs(resumen.get('racha', 0)) >= 3:
                    factores_destacados.append(f"Racha: {'Local en forma' if resumen['racha'] > 0 else 'Visitante en forma'}")
                
                if factores_destacados:
                    apuesta['factores_destacados'] = factores_destacados
            
            # Determinar nivel de confianza
            if apuesta['confianza'] >= 70:
                apuesta['nivel_confianza'] = 'ALTA'
            elif apuesta['confianza'] >= 55:
                apuesta['nivel_confianza'] = 'MEDIA'
            else:
                apuesta['nivel_confianza'] = 'BAJA'
            
            # Marcar si la predicción cambió con los factores avanzados
            apuesta['prediccion_modificada'] = prediccion_final != prediccion['prediccion']
            
            apuestas.append(apuesta)
        else:
            # No se encontró predicción
            if partido['numero'] == '15':
                apuestas.append({
                    'numero': partido['numero'],
                    'equipo_local': partido['equipo_local'],
                    'equipo_visitante': partido['equipo_visitante'],
                    'horario': partido['horario'],
                    'apuesta_recomendada': 'M',
                    'confianza': 0,
                    'probabilidades': {'0': 25.0, '1': 25.0, '2': 25.0, 'M': 25.0},
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
                    'apuesta_recomendada': 'X',
                    'confianza': 0,
                    'probabilidades': {'1': 33.33, 'X': 33.33, '2': 33.33},
                    'liga': 'No encontrada',
                    'fecha_partido': 'N/A',
                    'nivel_confianza': 'SIN DATOS',
                    'tipo_apuesta': '1X2',
                    'nota': 'No se encontró predicción para este partido'
                })
    
    return apuestas


def imprimir_boleto_quiniela_mejorado(apuestas):
    """Imprime el boleto de quiniela con formato bonito y factores avanzados"""
    print("\n" + "="*80)
    print("BOLETO QUINIELA - PREDICCIONES CON FACTORES AVANZADOS")
    print(f"Fecha de análisis: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("="*80)
    
    for apuesta in apuestas:
        tipo_apuesta = apuesta.get('tipo_apuesta', '1X2')
        
        if tipo_apuesta == 'GOLES':
            # Partido 15: apuesta de goles
            simbolo_apuesta = apuesta['apuesta_recomendada']
            
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
            print(f"    APUESTA GOLES: [{simbolo_apuesta}] {confianza_display} ({apuesta['nivel_confianza']})")
            if 'goles_esperados' in apuesta:
                print(f"    Goles esperados: {apuesta['goles_esperados']}")
            print(f"    Probs goles -> 0: {apuesta['probabilidades']['0']}% | 1: {apuesta['probabilidades']['1']}% | 2: {apuesta['probabilidades']['2']}% | M: {apuesta['probabilidades']['M']}%")
            
            if 'prediccion_ganador' in apuesta:
                simbolo_ganador = {'V': '1', 'E': 'X', 'D': '2'}.get(apuesta['prediccion_ganador'], apuesta['prediccion_ganador'])
                print(f"    GANADOR: [{simbolo_ganador}] {apuesta['confianza_ganador']}%")
                print(f"    Probs 1X2 -> 1: {apuesta['probabilidades_1x2']['1']}% | X: {apuesta['probabilidades_1x2']['X']}% | 2: {apuesta['probabilidades_1x2']['2']}%")
        else:
            # Partido normal 1X2
            simbolo_apuesta = {'V': '1', 'E': 'X', 'D': '2'}.get(apuesta['apuesta_recomendada'], apuesta['apuesta_recomendada'])
            
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
            
            # Mostrar si la predicción cambió
            if apuesta.get('prediccion_modificada'):
                simbolo_original = {'V': '1', 'E': 'X', 'D': '2'}.get(apuesta.get('apuesta_original'), '?')
                print(f"    [!] Predicción MODIFICADA: Original era [{simbolo_original}] con {apuesta.get('confianza_original')}%")
            
            # Mostrar factores destacados
            if 'factores_destacados' in apuesta:
                print(f"    Factores clave: {' | '.join(apuesta['factores_destacados'])}")
            
            # Mostrar resumen de factores avanzados
            if apuesta.get('factores_avanzados'):
                fa = apuesta['factores_avanzados']
                print(f"    Factores: Local={fa.get('localidad',0):+.1f} H2H={fa.get('h2h',0):+.1f} Racha={fa.get('racha',0):+.1f} Total={fa.get('total',0):+.1f}")
        
        if 'nota' in apuesta:
            print(f"    NOTA: {apuesta['nota']}")
    
    # Resumen
    print("\n" + "="*80)
    print("RESUMEN DE APUESTAS")
    print("="*80)
    
    apuestas_1 = sum(1 for a in apuestas if a['apuesta_recomendada'] in ['V', '1'])
    apuestas_x = sum(1 for a in apuestas if a['apuesta_recomendada'] in ['E', 'X'])
    apuestas_2 = sum(1 for a in apuestas if a['apuesta_recomendada'] in ['D', '2'])
    
    print(f"Total de partidos: {len(apuestas)}")
    print(f"Apuestas al 1 (Local): {apuestas_1}")
    print(f"Apuestas al X (Empate): {apuestas_x}")
    print(f"Apuestas al 2 (Visitante): {apuestas_2}")
    
    alta = sum(1 for a in apuestas if a['nivel_confianza'] == 'ALTA')
    media = sum(1 for a in apuestas if a['nivel_confianza'] == 'MEDIA')
    baja = sum(1 for a in apuestas if a['nivel_confianza'] == 'BAJA')
    sin_datos = sum(1 for a in apuestas if a['nivel_confianza'] == 'SIN DATOS')
    
    print(f"\nNivel de confianza:")
    print(f"  Alta (>=70%): {alta} partidos")
    print(f"  Media (55-69%): {media} partidos")
    print(f"  Baja (<55%): {baja} partidos")
    print(f"  Sin datos: {sin_datos} partidos")
    
    # Partidos modificados por factores avanzados
    modificados = sum(1 for a in apuestas if a.get('prediccion_modificada'))
    if modificados > 0:
        print(f"\n[!] Predicciones modificadas por factores avanzados: {modificados}")
    
    print("="*80)


def main():
    """Función principal"""
    base_dir = Path(__file__).parent.parent
    data_dir = base_dir / 'data'
    
    analisis_path = data_dir / 'analisis_futbol_espanol.json'
    futbol_completo_path = data_dir / 'futbol_espanol_completo.json'
    html_path = data_dir / 'Jornada_quiniela.html'
    output_path = data_dir / 'apuestas_quiniela_mejoradas.json'
    
    # Verificar archivos
    if not analisis_path.exists():
        print(f"Error: No se encuentra {analisis_path}")
        print("Ejecuta primero: python scrapper-futbol-espanol.py")
        return
    
    if not html_path.exists():
        print(f"Error: No se encuentra {html_path}")
        return
    
    print("="*70)
    print("ANÁLISIS DE QUINIELA CON FACTORES AVANZADOS")
    print("="*70)
    
    print("\nCargando análisis de fútbol español...")
    with open(analisis_path, 'r', encoding='utf-8') as f:
        analisis = json.load(f)
    
    predicciones_primera = analisis['predicciones']['primera_division']
    predicciones_segunda = analisis['predicciones']['segunda_division']
    
    print(f"[OK] Cargadas {len(predicciones_primera)} predicciones de Primera División")
    print(f"[OK] Cargadas {len(predicciones_segunda)} predicciones de Segunda División")
    
    # Cargar datos completos para factores avanzados
    datos_completos_primera = {}
    datos_completos_segunda = {}
    
    if futbol_completo_path.exists():
        print("\nCargando datos completos para factores avanzados...")
        with open(futbol_completo_path, 'r', encoding='utf-8') as f:
            datos_completos = json.load(f)
        
        # Los datos pueden estar bajo 'ligas' o directamente
        ligas = datos_completos.get('ligas', datos_completos)
        datos_completos_primera = ligas.get('primera_division', {})
        datos_completos_segunda = ligas.get('segunda_division', {})
        
        # Los partidos pueden estar en 'todos_partidos_jugados' o 'ultimos_resultados'
        partidos_primera = datos_completos_primera.get('todos_partidos_jugados', 
                            datos_completos_primera.get('ultimos_resultados', []))
        partidos_segunda = datos_completos_segunda.get('todos_partidos_jugados',
                            datos_completos_segunda.get('ultimos_resultados', []))
        # Actualizar la estructura para que el código funcione
        if 'todos_partidos_jugados' not in datos_completos_primera and 'ultimos_resultados' in datos_completos_primera:
            datos_completos_primera['todos_partidos_jugados'] = datos_completos_primera['ultimos_resultados']
        if 'todos_partidos_jugados' not in datos_completos_segunda and 'ultimos_resultados' in datos_completos_segunda:
            datos_completos_segunda['todos_partidos_jugados'] = datos_completos_segunda['ultimos_resultados']
        print(f"[OK] Cargados {len(partidos_primera)} partidos de Primera, {len(partidos_segunda)} de Segunda")
        print(f"[OK] Clasificación Primera: {len(datos_completos_primera.get('clasificacion', []))} equipos")
    else:
        print(f"\nAviso: No se encontró {futbol_completo_path}")
        print("Los factores avanzados funcionarán con datos limitados.")
    
    print("\nExtrayendo partidos del HTML de la quiniela...")
    partidos_quiniela = extraer_partidos_quiniela(html_path)
    print(f"[OK] Extraídos {len(partidos_quiniela)} partidos de la quiniela")
    
    print("\nGenerando apuestas con factores avanzados...")
    apuestas = generar_apuestas_quiniela_mejorado(
        partidos_quiniela, 
        predicciones_primera, 
        predicciones_segunda,
        datos_completos_primera,
        datos_completos_segunda,
        usar_factores_avanzados=True
    )
    
    # Guardar resultados
    resultado = {
        'fecha_analisis': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'version': '2.0 - Factores Avanzados',
        'total_partidos': len(apuestas),
        'apuestas': apuestas,
        'estadisticas': {
            'apuestas_1': sum(1 for a in apuestas if a['apuesta_recomendada'] in ['V', '1']),
            'apuestas_x': sum(1 for a in apuestas if a['apuesta_recomendada'] in ['E', 'X']),
            'apuestas_2': sum(1 for a in apuestas if a['apuesta_recomendada'] in ['D', '2']),
            'confianza_alta': sum(1 for a in apuestas if a['nivel_confianza'] == 'ALTA'),
            'confianza_media': sum(1 for a in apuestas if a['nivel_confianza'] == 'MEDIA'),
            'confianza_baja': sum(1 for a in apuestas if a['nivel_confianza'] == 'BAJA'),
            'sin_datos': sum(1 for a in apuestas if a['nivel_confianza'] == 'SIN DATOS'),
            'predicciones_modificadas': sum(1 for a in apuestas if a.get('prediccion_modificada'))
        }
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)
    
    print(f"\n[OK] Apuestas guardadas en: {output_path}")
    
    # Imprimir boleto
    imprimir_boleto_quiniela_mejorado(apuestas)


if __name__ == '__main__':
    main()
