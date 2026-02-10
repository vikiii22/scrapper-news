#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Módulo de factores avanzados para mejorar predicciones de quiniela
Incluye:
- Estadísticas local/visitante (home/away performance)
- Head-to-head (enfrentamientos directos)
- Racha de resultados
- Días de descanso
- Importancia del partido
"""

import json
import requests
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import unicodedata

# Configuración
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"

# Clima desactivado - no usar APIs externas
WEATHER_API_KEY = ""
WEATHER_ENABLED = False
_WEATHER_FAILED = True  # Desactivado permanentemente

# Coordenadas de ciudades de equipos españoles (aproximadas)
CIUDADES_EQUIPOS = {
    # Primera División
    'BARCELONA': {'lat': 41.38, 'lon': 2.18, 'ciudad': 'Barcelona'},
    'MADRID': {'lat': 40.42, 'lon': -3.70, 'ciudad': 'Madrid'},
    'ATLETICO': {'lat': 40.44, 'lon': -3.60, 'ciudad': 'Madrid'},
    'SEVILLA': {'lat': 37.39, 'lon': -5.99, 'ciudad': 'Sevilla'},
    'VALENCIA': {'lat': 39.47, 'lon': -0.38, 'ciudad': 'Valencia'},
    'VILLARREAL': {'lat': 39.94, 'lon': -0.10, 'ciudad': 'Villarreal'},
    'ATHLETIC': {'lat': 43.26, 'lon': -2.93, 'ciudad': 'Bilbao'},
    'SOCIEDAD': {'lat': 43.30, 'lon': -1.97, 'ciudad': 'San Sebastián'},
    'BETIS': {'lat': 37.36, 'lon': -5.98, 'ciudad': 'Sevilla'},
    'CELTA': {'lat': 42.21, 'lon': -8.74, 'ciudad': 'Vigo'},
    'OSASUNA': {'lat': 42.80, 'lon': -1.64, 'ciudad': 'Pamplona'},
    'GETAFE': {'lat': 40.33, 'lon': -3.71, 'ciudad': 'Getafe'},
    'MALLORCA': {'lat': 39.59, 'lon': 2.63, 'ciudad': 'Palma'},
    'GIRONA': {'lat': 41.96, 'lon': 2.82, 'ciudad': 'Girona'},
    'ALAVES': {'lat': 42.84, 'lon': -2.67, 'ciudad': 'Vitoria'},
    'ESPANYOL': {'lat': 41.35, 'lon': 2.08, 'ciudad': 'Barcelona'},
    'RAYO': {'lat': 40.39, 'lon': -3.66, 'ciudad': 'Madrid'},
    'PALMAS': {'lat': 28.10, 'lon': -15.43, 'ciudad': 'Las Palmas'},
    'LEGANES': {'lat': 40.33, 'lon': -3.76, 'ciudad': 'Leganés'},
    'VALLADOLID': {'lat': 41.65, 'lon': -4.72, 'ciudad': 'Valladolid'},
    
    # Segunda División
    'OVIEDO': {'lat': 43.36, 'lon': -5.85, 'ciudad': 'Oviedo'},
    'SPORTING': {'lat': 43.54, 'lon': -5.64, 'ciudad': 'Gijón'},
    'ZARAGOZA': {'lat': 41.65, 'lon': -0.88, 'ciudad': 'Zaragoza'},
    'RACING': {'lat': 43.46, 'lon': -3.80, 'ciudad': 'Santander'},
    'EIBAR': {'lat': 43.18, 'lon': -2.47, 'ciudad': 'Éibar'},
    'LEVANTE': {'lat': 39.49, 'lon': -0.35, 'ciudad': 'Valencia'},
    'HUESCA': {'lat': 42.14, 'lon': -0.41, 'ciudad': 'Huesca'},
    'CADIZ': {'lat': 36.53, 'lon': -6.30, 'ciudad': 'Cádiz'},
    'ALMERIA': {'lat': 36.84, 'lon': -2.46, 'ciudad': 'Almería'},
    'ELCHE': {'lat': 38.27, 'lon': -0.70, 'ciudad': 'Elche'},
    'TENERIFE': {'lat': 28.47, 'lon': -16.25, 'ciudad': 'Santa Cruz'},
    'GRANADA': {'lat': 37.13, 'lon': -3.60, 'ciudad': 'Granada'},
    'BURGOS': {'lat': 42.34, 'lon': -3.70, 'ciudad': 'Burgos'},
    'MIRANDES': {'lat': 42.68, 'lon': -2.94, 'ciudad': 'Miranda de Ebro'},
    'ALBACETE': {'lat': 38.99, 'lon': -1.86, 'ciudad': 'Albacete'},
    'CASTELLON': {'lat': 39.99, 'lon': -0.04, 'ciudad': 'Castellón'},
    'DEPORTIVO': {'lat': 43.37, 'lon': -8.41, 'ciudad': 'A Coruña'},
    'CORDOBA': {'lat': 37.88, 'lon': -4.77, 'ciudad': 'Córdoba'},
    'MALAGA': {'lat': 36.72, 'lon': -4.42, 'ciudad': 'Málaga'},
    'LEONESA': {'lat': 42.60, 'lon': -5.57, 'ciudad': 'León'},
    'CEUTA': {'lat': 35.89, 'lon': -5.32, 'ciudad': 'Ceuta'},
}


class FactoresAvanzados:
    """Clase para calcular factores avanzados de predicción"""
    
    def __init__(self, datos_primera: dict = None, datos_segunda: dict = None):
        self.datos_primera = datos_primera or {}
        self.datos_segunda = datos_segunda or {}
        self._cache_clima = {}
        self._cache_h2h = {}
        
        # Crear directorio de caché si no existe
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        
        # Cargar caché de clima
        self._cargar_cache_clima()
    
    def _cargar_cache_clima(self):
        """Carga el caché de clima desde archivo"""
        cache_file = CACHE_DIR / "weather_cache.json"
        if cache_file.exists():
            with open(cache_file, 'r', encoding='utf-8') as f:
                self._cache_clima = json.load(f)
    
    def _guardar_cache_clima(self):
        """Guarda el caché de clima a archivo"""
        cache_file = CACHE_DIR / "weather_cache.json"
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(self._cache_clima, f, ensure_ascii=False, indent=2)
    
    # =========================================================================
    # FACTOR 1: ESTADÍSTICAS LOCAL/VISITANTE
    # =========================================================================
    
    def calcular_rendimiento_local_visitante(
        self, 
        equipo: str, 
        partidos_jugados: List[dict],
        es_local: bool
    ) -> dict:
        """
        Calcula el rendimiento de un equipo como local o visitante
        
        Returns:
            dict con: victorias, empates, derrotas, goles_favor, goles_contra, puntos, partidos
        """
        stats = {
            'partidos': 0,
            'victorias': 0,
            'empates': 0,
            'derrotas': 0,
            'goles_favor': 0,
            'goles_contra': 0,
            'puntos': 0
        }
        
        for partido in partidos_jugados:
            es_partido_local = partido.get('equipo_local', '').upper() == equipo.upper()
            es_partido_visitante = partido.get('equipo_visitante', '').upper() == equipo.upper()
            
            # Filtrar según si buscamos partidos de local o visitante
            if es_local and not es_partido_local:
                continue
            if not es_local and not es_partido_visitante:
                continue
            
            goles_local = partido.get('goles_local', 0) or 0
            goles_visitante = partido.get('goles_visitante', 0) or 0
            
            stats['partidos'] += 1
            
            if es_partido_local:
                stats['goles_favor'] += goles_local
                stats['goles_contra'] += goles_visitante
                
                if goles_local > goles_visitante:
                    stats['victorias'] += 1
                    stats['puntos'] += 3
                elif goles_local == goles_visitante:
                    stats['empates'] += 1
                    stats['puntos'] += 1
                else:
                    stats['derrotas'] += 1
            else:  # Visitante
                stats['goles_favor'] += goles_visitante
                stats['goles_contra'] += goles_local
                
                if goles_visitante > goles_local:
                    stats['victorias'] += 1
                    stats['puntos'] += 3
                elif goles_visitante == goles_local:
                    stats['empates'] += 1
                    stats['puntos'] += 1
                else:
                    stats['derrotas'] += 1
        
        # Calcular promedios
        if stats['partidos'] > 0:
            stats['puntos_por_partido'] = round(stats['puntos'] / stats['partidos'], 2)
            stats['goles_favor_promedio'] = round(stats['goles_favor'] / stats['partidos'], 2)
            stats['goles_contra_promedio'] = round(stats['goles_contra'] / stats['partidos'], 2)
            stats['porcentaje_victorias'] = round(
                (stats['victorias'] / stats['partidos']) * 100, 2
            )
        else:
            stats['puntos_por_partido'] = 0
            stats['goles_favor_promedio'] = 0
            stats['goles_contra_promedio'] = 0
            stats['porcentaje_victorias'] = 0
        
        return stats
    
    def calcular_factor_localidad_avanzado(
        self, 
        equipo_local: str, 
        equipo_visitante: str,
        partidos_jugados: List[dict]
    ) -> dict:
        """
        Calcula un factor de localidad más preciso basado en el rendimiento
        real de cada equipo como local y visitante
        
        Returns:
            dict con factor_localidad, stats_local, stats_visitante
        """
        # Stats del local jugando EN CASA
        stats_local_en_casa = self.calcular_rendimiento_local_visitante(
            equipo_local, partidos_jugados, es_local=True
        )
        
        # Stats del visitante jugando FUERA
        stats_visitante_fuera = self.calcular_rendimiento_local_visitante(
            equipo_visitante, partidos_jugados, es_local=False
        )
        
        # Calcular factor de localidad
        # Base: 5 puntos (ventaja típica de local)
        factor_base = 5.0
        
        # Ajuste por rendimiento del local en casa
        # Si el local gana mucho en casa, aumentar el factor
        if stats_local_en_casa['partidos'] >= 3:
            ajuste_local = (stats_local_en_casa['puntos_por_partido'] - 1.5) * 2
            # 1.5 es el promedio neutral (empatar siempre)
            # Si gana más, ajuste positivo; si pierde más, negativo
        else:
            ajuste_local = 0
        
        # Ajuste por rendimiento del visitante fuera
        # Si el visitante gana mucho fuera, reducir el factor de localidad
        if stats_visitante_fuera['partidos'] >= 3:
            ajuste_visitante = (1.0 - stats_visitante_fuera['puntos_por_partido']) * 2
            # Si el visitante gana mucho fuera (>1.5 ppp), reducir ventaja local
        else:
            ajuste_visitante = 0
        
        factor_final = factor_base + ajuste_local + ajuste_visitante
        factor_final = max(0, min(15, factor_final))  # Limitar entre 0 y 15
        
        return {
            'factor_localidad': round(factor_final, 2),
            'factor_base': factor_base,
            'ajuste_local': round(ajuste_local, 2),
            'ajuste_visitante': round(ajuste_visitante, 2),
            'stats_local_en_casa': stats_local_en_casa,
            'stats_visitante_fuera': stats_visitante_fuera
        }
    
    # =========================================================================
    # FACTOR 2: HEAD-TO-HEAD (Enfrentamientos directos)
    # =========================================================================
    
    def obtener_h2h(
        self, 
        equipo1: str, 
        equipo2: str, 
        partidos_jugados: List[dict],
        ultimos_n: int = 10
    ) -> dict:
        """
        Obtiene el historial de enfrentamientos directos entre dos equipos
        
        Returns:
            dict con historial de partidos y estadísticas
        """
        enfrentamientos = []
        
        for partido in partidos_jugados:
            local = partido.get('equipo_local', '').upper()
            visitante = partido.get('equipo_visitante', '').upper()
            
            # Verificar si es un enfrentamiento entre estos equipos
            es_enfrentamiento = (
                (equipo1.upper() in local or local in equipo1.upper()) and
                (equipo2.upper() in visitante or visitante in equipo2.upper())
            ) or (
                (equipo2.upper() in local or local in equipo2.upper()) and
                (equipo1.upper() in visitante or visitante in equipo1.upper())
            )
            
            if es_enfrentamiento:
                enfrentamientos.append(partido)
        
        # Ordenar por fecha (más reciente primero) y tomar últimos N
        enfrentamientos = enfrentamientos[-ultimos_n:]
        
        # Calcular estadísticas
        equipo1_upper = equipo1.upper()
        stats = {
            'victorias_equipo1': 0,
            'empates': 0,
            'victorias_equipo2': 0,
            'goles_equipo1': 0,
            'goles_equipo2': 0,
            'partidos_analizados': len(enfrentamientos)
        }
        
        for partido in enfrentamientos:
            local = partido.get('equipo_local', '').upper()
            goles_local = partido.get('goles_local', 0) or 0
            goles_visitante = partido.get('goles_visitante', 0) or 0
            
            # Determinar si equipo1 era local o visitante
            equipo1_era_local = equipo1_upper in local
            
            if equipo1_era_local:
                stats['goles_equipo1'] += goles_local
                stats['goles_equipo2'] += goles_visitante
                
                if goles_local > goles_visitante:
                    stats['victorias_equipo1'] += 1
                elif goles_local < goles_visitante:
                    stats['victorias_equipo2'] += 1
                else:
                    stats['empates'] += 1
            else:
                stats['goles_equipo1'] += goles_visitante
                stats['goles_equipo2'] += goles_local
                
                if goles_visitante > goles_local:
                    stats['victorias_equipo1'] += 1
                elif goles_visitante < goles_local:
                    stats['victorias_equipo2'] += 1
                else:
                    stats['empates'] += 1
        
        return {
            'enfrentamientos': enfrentamientos,
            'stats': stats
        }
    
    def calcular_factor_h2h(
        self, 
        equipo_local: str, 
        equipo_visitante: str,
        partidos_jugados: List[dict]
    ) -> dict:
        """
        Calcula el factor de ajuste basado en enfrentamientos directos
        
        Returns:
            dict con factor y estadísticas H2H
        """
        h2h = self.obtener_h2h(equipo_local, equipo_visitante, partidos_jugados)
        stats = h2h['stats']
        
        if stats['partidos_analizados'] == 0:
            return {
                'factor_h2h': 0,
                'h2h_disponible': False,
                'stats': stats
            }
        
        # Calcular dominio histórico
        total_partidos = stats['partidos_analizados']
        dominio_local = (stats['victorias_equipo1'] - stats['victorias_equipo2']) / total_partidos
        
        # Factor H2H: -3 a +3 puntos
        factor_h2h = dominio_local * 3
        factor_h2h = max(-3, min(3, factor_h2h))
        
        return {
            'factor_h2h': round(factor_h2h, 2),
            'h2h_disponible': True,
            'stats': stats,
            'dominio_historico': 'local' if dominio_local > 0.2 else ('visitante' if dominio_local < -0.2 else 'equilibrado')
        }
    
    # =========================================================================
    # FACTOR 3: CLIMATOLOGÍA
    # =========================================================================
    
    def obtener_clima(
        self, 
        equipo_local_norm: str, 
        fecha_partido: str = None
    ) -> Optional[dict]:
        """
        Obtiene información del clima para la ciudad del equipo local
        Usa OpenWeatherMap API (requiere API key gratuita)
        
        Returns:
            dict con información del clima o None si no disponible
        """
        global _WEATHER_FAILED
        
        if not WEATHER_ENABLED or _WEATHER_FAILED:
            return None
        
        # Buscar coordenadas del equipo
        coords = CIUDADES_EQUIPOS.get(equipo_local_norm.upper())
        if not coords:
            return None
        
        # Verificar caché (válido por 3 horas)
        cache_key = f"{equipo_local_norm}_{datetime.now().strftime('%Y%m%d_%H')}"
        if cache_key in self._cache_clima:
            return self._cache_clima[cache_key]
        
        try:
            # API 3.0 OneCall - excluimos minutely, hourly, daily, alerts para solo obtener current
            url = f"https://api.openweathermap.org/data/3.0/onecall"
            params = {
                'lat': coords['lat'],
                'lon': coords['lon'],
                'appid': WEATHER_API_KEY,
                'units': 'metric',
                'lang': 'es',
                'exclude': 'minutely,hourly,daily,alerts'
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            # Si hay error 401 (Unauthorized), desactivar clima para esta sesión
            if response.status_code == 401:
                print(f"[Clima] API key no válida o no activada. Desactivando clima.")
                print(f"[Clima] Las nuevas API keys pueden tardar unas horas en activarse.")
                _WEATHER_FAILED = True
                return None
            
            response.raise_for_status()
            data = response.json()
            
            # La API 3.0 tiene estructura diferente - usa 'current' para datos actuales
            current = data.get('current', {})
            weather_info = current.get('weather', [{}])[0]
            
            clima = {
                'ciudad': coords['ciudad'],
                'temperatura': current.get('temp', 0),
                'sensacion_termica': current.get('feels_like', 0),
                'humedad': current.get('humidity', 0),
                'viento_velocidad': current.get('wind_speed', 0),
                'descripcion': weather_info.get('description', ''),
                'condicion': weather_info.get('main', ''),
                'lluvia': current.get('rain', {}).get('1h', 0),
                'nieve': current.get('snow', {}).get('1h', 0),
                'nubosidad': current.get('clouds', 0)
            }
            
            # Guardar en caché
            self._cache_clima[cache_key] = clima
            self._guardar_cache_clima()
            
            return clima
            
        except requests.exceptions.HTTPError as e:
            if '401' in str(e):
                print(f"[Clima] API key no autorizada. Desactivando clima.")
                _WEATHER_FAILED = True
            return None
        except Exception as e:
            # Solo mostrar error si no es un problema conocido
            if 'timeout' not in str(e).lower():
                print(f"[Clima] Error: {e}")
            return None
    
    def calcular_factor_clima(
        self, 
        equipo_local_norm: str,
        equipo_visitante_norm: str
    ) -> dict:
        """
        Calcula el factor de ajuste basado en condiciones climáticas
        
        Considera:
        - Lluvia/nieve: Puede favorecer a equipos defensivos
        - Viento fuerte: Afecta juego aéreo
        - Temperaturas extremas: Puede afectar rendimiento
        - Equipos del norte vs sur (adaptación al clima)
        
        Returns:
            dict con factor y detalles del clima
        """
        clima = self.obtener_clima(equipo_local_norm)
        
        if not clima:
            return {
                'factor_clima': 0,
                'clima_disponible': False,
                'razon': 'No se pudo obtener información del clima'
            }
        
        factor = 0.0
        factores_detalle = []
        
        # Factor lluvia (favorece equipos defensivos y locales acostumbrados)
        if clima['lluvia'] > 0 or 'lluvia' in clima['descripcion'].lower():
            factor += 1.0  # Pequeña ventaja al local (acostumbrado)
            factores_detalle.append('Lluvia: +1 local')
        
        # Factor nieve (gran impacto)
        if clima['nieve'] > 0:
            factor += 2.0  # Mayor ventaja al local
            factores_detalle.append('Nieve: +2 local')
        
        # Factor viento fuerte (>40 km/h)
        if clima['viento_velocidad'] > 11:  # ~40 km/h
            factor += 0.5
            factores_detalle.append('Viento fuerte: +0.5 local')
        
        # Factor temperatura extrema
        if clima['temperatura'] < 5:
            # Frío extremo - verificar si el visitante viene del sur
            visitante_coords = CIUDADES_EQUIPOS.get(equipo_visitante_norm.upper(), {})
            if visitante_coords.get('lat', 40) < 38:  # Equipos del sur
                factor += 1.5
                factores_detalle.append('Frío extremo (visitante del sur): +1.5 local')
        elif clima['temperatura'] > 30:
            # Calor extremo - verificar si el visitante viene del norte
            visitante_coords = CIUDADES_EQUIPOS.get(equipo_visitante_norm.upper(), {})
            if visitante_coords.get('lat', 40) > 42:  # Equipos del norte
                factor += 1.0
                factores_detalle.append('Calor extremo (visitante del norte): +1 local')
        
        return {
            'factor_clima': round(factor, 2),
            'clima_disponible': True,
            'clima': clima,
            'factores_detalle': factores_detalle
        }
    
    # =========================================================================
    # FACTOR 4: RACHA DE RESULTADOS
    # =========================================================================
    
    def calcular_racha(
        self, 
        equipo: str, 
        partidos_jugados: List[dict],
        ultimos_n: int = 5
    ) -> dict:
        """
        Calcula la racha de resultados de un equipo
        
        Returns:
            dict con racha actual, puntos, tipo de racha
        """
        partidos_equipo = []
        
        for partido in partidos_jugados:
            local = partido.get('equipo_local', '').upper()
            visitante = partido.get('equipo_visitante', '').upper()
            equipo_upper = equipo.upper()
            
            if equipo_upper in local or local in equipo_upper:
                goles_local = partido.get('goles_local', 0) or 0
                goles_visitante = partido.get('goles_visitante', 0) or 0
                
                if goles_local > goles_visitante:
                    resultado = 'V'
                    puntos = 3
                elif goles_local == goles_visitante:
                    resultado = 'E'
                    puntos = 1
                else:
                    resultado = 'D'
                    puntos = 0
                    
                partidos_equipo.append({
                    'resultado': resultado,
                    'puntos': puntos,
                    'como': 'local'
                })
                
            elif equipo_upper in visitante or visitante in equipo_upper:
                goles_local = partido.get('goles_local', 0) or 0
                goles_visitante = partido.get('goles_visitante', 0) or 0
                
                if goles_visitante > goles_local:
                    resultado = 'V'
                    puntos = 3
                elif goles_visitante == goles_local:
                    resultado = 'E'
                    puntos = 1
                else:
                    resultado = 'D'
                    puntos = 0
                    
                partidos_equipo.append({
                    'resultado': resultado,
                    'puntos': puntos,
                    'como': 'visitante'
                })
        
        # Tomar últimos N partidos
        ultimos = partidos_equipo[-ultimos_n:]
        
        if not ultimos:
            return {
                'racha': '',
                'puntos': 0,
                'max_puntos': 0,
                'porcentaje': 0,
                'tipo_racha': 'desconocida',
                'partidos_analizados': 0,
                'racha_actual': {
                    'tipo': None,
                    'cantidad': 0
                }
            }
        
        racha_str = ''.join([p['resultado'] for p in ultimos])
        puntos_totales = sum([p['puntos'] for p in ultimos])
        max_puntos = len(ultimos) * 3
        
        # Determinar tipo de racha
        if puntos_totales >= max_puntos * 0.8:
            tipo_racha = 'excelente'
        elif puntos_totales >= max_puntos * 0.6:
            tipo_racha = 'buena'
        elif puntos_totales >= max_puntos * 0.4:
            tipo_racha = 'regular'
        elif puntos_totales >= max_puntos * 0.2:
            tipo_racha = 'mala'
        else:
            tipo_racha = 'muy_mala'
        
        # Contar racha actual (consecutivos del mismo tipo)
        racha_actual = 1
        ultimo_resultado = ultimos[-1]['resultado'] if ultimos else None
        for i in range(len(ultimos) - 2, -1, -1):
            if ultimos[i]['resultado'] == ultimo_resultado:
                racha_actual += 1
            else:
                break
        
        return {
            'racha': racha_str,
            'puntos': puntos_totales,
            'max_puntos': max_puntos,
            'porcentaje': round((puntos_totales / max_puntos) * 100, 2) if max_puntos > 0 else 0,
            'tipo_racha': tipo_racha,
            'partidos_analizados': len(ultimos),
            'racha_actual': {
                'tipo': ultimo_resultado,
                'cantidad': racha_actual
            }
        }
    
    def calcular_factor_racha(
        self, 
        equipo_local: str, 
        equipo_visitante: str,
        partidos_jugados: List[dict]
    ) -> dict:
        """
        Calcula el factor de ajuste basado en las rachas de ambos equipos
        
        Returns:
            dict con factor y rachas de ambos equipos
        """
        racha_local = self.calcular_racha(equipo_local, partidos_jugados)
        racha_visitante = self.calcular_racha(equipo_visitante, partidos_jugados)
        
        # Calcular diferencia de rendimiento reciente (con valores por defecto)
        porcentaje_local = racha_local.get('porcentaje', 0)
        porcentaje_visitante = racha_visitante.get('porcentaje', 0)
        diff_porcentaje = porcentaje_local - porcentaje_visitante
        
        # Factor: -5 a +5 puntos basado en diferencia de forma
        factor_racha = diff_porcentaje / 20  # 100% diff = 5 puntos
        factor_racha = max(-5, min(5, factor_racha))
        
        # Bonus por racha positiva/negativa extrema
        racha_actual_local = racha_local.get('racha_actual', {})
        racha_actual_visitante = racha_visitante.get('racha_actual', {})
        
        if racha_actual_local.get('tipo') == 'V' and racha_actual_local.get('cantidad', 0) >= 3:
            factor_racha += 1  # Bonus por 3+ victorias consecutivas
        if racha_actual_visitante.get('tipo') == 'V' and racha_actual_visitante.get('cantidad', 0) >= 3:
            factor_racha -= 1  # Bonus al visitante
        
        if racha_actual_local.get('tipo') == 'D' and racha_actual_local.get('cantidad', 0) >= 3:
            factor_racha -= 1  # Penalización al local por mala racha
        if racha_actual_visitante.get('tipo') == 'D' and racha_actual_visitante.get('cantidad', 0) >= 3:
            factor_racha += 1  # Bonus al local
        
        return {
            'factor_racha': round(factor_racha, 2),
            'racha_local': racha_local,
            'racha_visitante': racha_visitante
        }
    
    # =========================================================================
    # FACTOR 5: DÍAS DE DESCANSO
    # =========================================================================
    
    def calcular_dias_descanso(
        self, 
        equipo: str, 
        partidos_jugados: List[dict],
        fecha_partido: str = None
    ) -> int:
        """
        Calcula los días de descanso desde el último partido
        
        Returns:
            int con días de descanso (-1 si no se puede calcular)
        """
        # Buscar último partido del equipo
        ultimo_partido = None
        
        for partido in reversed(partidos_jugados):
            local = partido.get('equipo_local', '').upper()
            visitante = partido.get('equipo_visitante', '').upper()
            equipo_upper = equipo.upper()
            
            if equipo_upper in local or local in equipo_upper or \
               equipo_upper in visitante or visitante in equipo_upper:
                ultimo_partido = partido
                break
        
        if not ultimo_partido or 'fecha' not in ultimo_partido:
            return -1
        
        try:
            fecha_ultimo = datetime.strptime(ultimo_partido['fecha'], '%Y-%m-%d')
            fecha_actual = datetime.strptime(fecha_partido, '%Y-%m-%d') if fecha_partido else datetime.now()
            
            dias = (fecha_actual - fecha_ultimo).days
            return max(0, dias)
        except:
            return -1
    
    def calcular_factor_descanso(
        self, 
        equipo_local: str, 
        equipo_visitante: str,
        partidos_jugados: List[dict],
        fecha_partido: str = None
    ) -> dict:
        """
        Calcula el factor de ajuste basado en días de descanso
        
        Returns:
            dict con factor y días de descanso de cada equipo
        """
        dias_local = self.calcular_dias_descanso(equipo_local, partidos_jugados, fecha_partido)
        dias_visitante = self.calcular_dias_descanso(equipo_visitante, partidos_jugados, fecha_partido)
        
        if dias_local < 0 or dias_visitante < 0:
            return {
                'factor_descanso': 0,
                'disponible': False,
                'dias_local': dias_local,
                'dias_visitante': dias_visitante
            }
        
        # Calcular ventaja por descanso
        # El equipo con más descanso tiene ventaja, pero solo si la diferencia es significativa
        diff_dias = dias_local - dias_visitante
        
        # Factor: pequeño (-2 a +2)
        if diff_dias >= 4:
            factor = 2.0  # Local tiene mucho más descanso
        elif diff_dias >= 2:
            factor = 1.0
        elif diff_dias <= -4:
            factor = -2.0  # Visitante tiene mucho más descanso
        elif diff_dias <= -2:
            factor = -1.0
        else:
            factor = 0
        
        # Penalización por muy poco descanso (< 3 días)
        if dias_local < 3:
            factor -= 1.0
        if dias_visitante < 3:
            factor += 1.0
        
        return {
            'factor_descanso': round(factor, 2),
            'disponible': True,
            'dias_local': dias_local,
            'dias_visitante': dias_visitante,
            'diferencia': diff_dias
        }
    
    # =========================================================================
    # FACTOR 6: IMPORTANCIA DEL PARTIDO
    # =========================================================================
    
    def calcular_importancia_partido(
        self, 
        equipo: str, 
        clasificacion: List[dict],
        total_jornadas: int = 38
    ) -> dict:
        """
        Calcula la importancia del partido para el equipo
        basándose en su posición en la tabla y lo que se juega
        
        Returns:
            dict con nivel de importancia y motivación extra
        """
        # Buscar equipo en clasificación
        datos_equipo = None
        for e in clasificacion:
            nombre = e.get('equipo', e.get('team', {}).get('name', '')).upper()
            if equipo.upper() in nombre or nombre in equipo.upper():
                datos_equipo = e
                break
        
        if not datos_equipo:
            return {
                'importancia': 'normal',
                'factor_importancia': 0,
                'motivo': 'No se encontró en clasificación'
            }
        
        posicion = datos_equipo.get('posicion', datos_equipo.get('position', 10))
        puntos = datos_equipo.get('puntos', datos_equipo.get('points', 0))
        partidos_jugados = datos_equipo.get('jugados', datos_equipo.get('partidos_jugados', datos_equipo.get('matches', 20)))
        total_equipos = len(clasificacion) if clasificacion else 20
        
        # Zonas de la tabla
        zona_champions = 4  # Primeros 4
        zona_europa = 6  # Primeros 6-7
        zona_descenso = total_equipos - 3  # Últimos 3
        
        importancia = 'normal'
        factor = 0
        motivo = ''
        
        # Lucha por el título
        if posicion <= 2:
            importancia = 'muy_alta'
            factor = 2.0
            motivo = 'Lucha por el título'
        # Lucha por Champions
        elif posicion <= zona_champions + 2:
            importancia = 'alta'
            factor = 1.5
            motivo = 'Lucha por Champions League'
        # Lucha por Europa
        elif posicion <= zona_europa + 2:
            importancia = 'media-alta'
            factor = 1.0
            motivo = 'Lucha por Europa League'
        # Zona de descenso
        elif posicion >= zona_descenso - 2:
            importancia = 'muy_alta'
            factor = 2.0
            motivo = 'Lucha por evitar descenso'
        # Zona tranquila
        else:
            importancia = 'normal'
            factor = 0
            motivo = 'Sin objetivos inmediatos'
        
        return {
            'importancia': importancia,
            'factor_importancia': factor,
            'motivo': motivo,
            'posicion': posicion,
            'puntos': puntos
        }
    
    def calcular_factor_importancia(
        self, 
        equipo_local: str, 
        equipo_visitante: str,
        clasificacion: List[dict]
    ) -> dict:
        """
        Calcula el factor de motivación basado en la importancia para cada equipo
        
        Returns:
            dict con factor y detalles de importancia
        """
        importancia_local = self.calcular_importancia_partido(equipo_local, clasificacion)
        importancia_visitante = self.calcular_importancia_partido(equipo_visitante, clasificacion)
        
        # La diferencia de importancia puede afectar el resultado
        # Si el local se juega más, puede estar más motivado
        factor = importancia_local['factor_importancia'] - importancia_visitante['factor_importancia']
        
        return {
            'factor_importancia': round(factor, 2),
            'importancia_local': importancia_local,
            'importancia_visitante': importancia_visitante
        }
    
    # =========================================================================
    # MÉTODO COMBINADO: TODOS LOS FACTORES AVANZADOS
    # =========================================================================
    
    def calcular_todos_factores(
        self, 
        equipo_local: str,
        equipo_local_norm: str,
        equipo_visitante: str,
        equipo_visitante_norm: str,
        partidos_jugados: List[dict],
        clasificacion: List[dict],
        fecha_partido: str = None
    ) -> dict:
        """
        Calcula todos los factores avanzados para un partido
        
        Returns:
            dict con todos los factores y un score combinado
        """
        factores = {}
        
        # 1. Factor localidad avanzado
        factores['localidad'] = self.calcular_factor_localidad_avanzado(
            equipo_local, equipo_visitante, partidos_jugados
        )
        
        # 2. Factor H2H
        factores['h2h'] = self.calcular_factor_h2h(
            equipo_local, equipo_visitante, partidos_jugados
        )
        
        # 3. Factor clima
        factores['clima'] = self.calcular_factor_clima(
            equipo_local_norm, equipo_visitante_norm
        )
        
        # 4. Factor racha
        factores['racha'] = self.calcular_factor_racha(
            equipo_local, equipo_visitante, partidos_jugados
        )
        
        # 5. Factor descanso
        factores['descanso'] = self.calcular_factor_descanso(
            equipo_local, equipo_visitante, partidos_jugados, fecha_partido
        )
        
        # 6. Factor importancia
        factores['importancia'] = self.calcular_factor_importancia(
            equipo_local, equipo_visitante, clasificacion
        )
        
        # Calcular factor combinado
        factor_total = (
            factores['localidad']['factor_localidad'] +
            factores['h2h']['factor_h2h'] +
            factores['clima']['factor_clima'] +
            factores['racha']['factor_racha'] +
            factores['descanso']['factor_descanso'] +
            factores['importancia']['factor_importancia']
        )
        
        # Detalle de contribución de cada factor
        detalle = {
            'localidad': factores['localidad']['factor_localidad'],
            'h2h': factores['h2h']['factor_h2h'],
            'clima': factores['clima']['factor_clima'],
            'racha': factores['racha']['factor_racha'],
            'descanso': factores['descanso']['factor_descanso'],
            'importancia': factores['importancia']['factor_importancia'],
            'total': round(factor_total, 2)
        }
        
        return {
            'factores': factores,
            'resumen': detalle,
            'factor_total': round(factor_total, 2)
        }


# =========================================================================
# FUNCIÓN DE PRUEBA
# =========================================================================

def test_factores():
    """Prueba el módulo de factores avanzados"""
    print("=" * 70)
    print("TEST: Módulo de Factores Avanzados")
    print("=" * 70)
    
    # Cargar datos de ejemplo
    try:
        with open(DATA_DIR / 'futbol_espanol_completo.json', 'r', encoding='utf-8') as f:
            datos = json.load(f)
        
        primera = datos.get('primera_division', {})
        partidos = primera.get('todos_partidos_jugados', [])
        clasificacion = primera.get('clasificacion', [])
        
        print(f"[OK] Cargados {len(partidos)} partidos y {len(clasificacion)} equipos")
        
        # Crear instancia
        fa = FactoresAvanzados()
        
        # Probar con un partido de ejemplo
        print("\n--- Test: Barcelona vs Real Madrid ---")
        
        resultado = fa.calcular_todos_factores(
            equipo_local='Barcelona',
            equipo_local_norm='BARCELONA',
            equipo_visitante='Real Madrid',
            equipo_visitante_norm='MADRID',
            partidos_jugados=partidos,
            clasificacion=clasificacion,
            fecha_partido='2026-02-15'
        )
        
        print(f"\nResumen de factores:")
        for factor, valor in resultado['resumen'].items():
            print(f"  {factor}: {valor}")
        
        print(f"\n[OK] Factor total: {resultado['factor_total']}")
        
    except Exception as e:
        print(f"[FALLO] Error en test: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    test_factores()
