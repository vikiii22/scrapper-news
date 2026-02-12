"""Utilidades para normalizar nombres de equipos."""
import unicodedata
from typing import Dict

def remove_accents(input_str: str) -> str:
    """Elimina acentos de un string."""
    if not input_str:
        return ""
    # Normalizar unicode (NFKD separa caracteres base de marcas)
    nfkd_form = unicodedata.normalize('NFKD', str(input_str))
    # Filtrar marcas de combinación (acentos, diéresis, etc.) y unir
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

# Mapeo de nombres normalizados (MAYÚSCULAS SIN ACENTOS) a nombre estándar
# La clave debe estar en MAYÚSCULAS y SIN ACENTOS para coincidir con la lógica
# El valor es el nombre preferido (Title Case)
TEAM_NAME_MAPPINGS = {
    "R.MADRID": "Real Madrid",
    "R. MADRID": "Real Madrid",
    "REAL MADRID": "Real Madrid",
    
    "R.SOCIEDAD": "Real Sociedad",
    "R. SOCIEDAD": "Real Sociedad",
    "REAL SOCIEDAD": "Real Sociedad",
    
    "ATH.CLUB": "Athletic Club",
    "ATH. CLUB": "Athletic Club",
    "ATHLETIC CLUB": "Athletic Club",
    "ATHLETIC": "Athletic Club",
    "ATH. BILBAO": "Athletic Club",
    
    "ATL.MADRID": "Atletico Madrid",
    "ATL. MADRID": "Atletico Madrid",
    "ATLETICO MADRID": "Atletico Madrid",
    "ATLETICO DE MADRID": "Atletico Madrid",
    "ATLETICO": "Atletico Madrid",
    
    "R.OVIEDO": "Real Oviedo",
    "REAL OVIEDO": "Real Oviedo",
    
    "R.BETIS": "Betis",
    "REAL BETIS": "Betis",
    "BETIS": "Betis",
    
    "R.VALLADOLID": "Valladolid",
    "REAL VALLADOLID": "Valladolid",
    "VALLADOLID": "Valladolid",
    
    "R.ZARAGOZA": "Zaragoza",
    "REAL ZARAGOZA": "Zaragoza",
    "ZARAGOZA": "Zaragoza",
    
    "SP.GIJON": "Sporting Gijon",
    "SPORTING GIJON": "Sporting Gijon",
    "SPORTING": "Sporting Gijon",
    
    "R.RACING C.": "Racing Santander",
    "RACING SANTANDER": "Racing Santander",
    "RACING": "Racing Santander",
    
    "CELTA": "Celta Vigo",
    "RC CELTA": "Celta Vigo",
    "CELTA DE VIGO": "Celta Vigo",
    
    "ESPANYOL": "Espanyol",
    "RCD ESPANYOL": "Espanyol",
    "ESPANOL": "Espanyol",
    
    "RAYO": "Rayo Vallecano",
    "RAYO VALLECANO": "Rayo Vallecano",
    
    "ALAVES": "Alaves",
    "DEPORTIVO ALAVES": "Alaves",
    
    "CADIZ": "Cadiz",
    
    "ALMERIA": "Almeria",
    "UD ALMERIA": "Almeria",
    
    "MALAGA": "Malaga",
    
    "LEGANES": "Leganes",
    
    "MIRANDES": "Mirandes",

    "CASTELLON": "Castellon",
    
    "CORDOBA": "Cordoba",
    
    "DEPORTIVO": "Deportivo La Coruna",
    "RC DEPORTIVO": "Deportivo La Coruna",
    "DEPORTIVO LA CORUNA": "Deportivo La Coruna",
    
    "ELDENSE": "Eldense",
    "FERROL": "Racing Ferrol",
    "RACING FERROL": "Racing Ferrol",
    
    "BARCELONA": "Barcelona",
    "FC BARCELONA": "Barcelona",
    
    "SEVILLA": "Sevilla",
    "FC SEVILLA": "Sevilla",
    
    "VALENCIA": "Valencia",
    "FC VALENCIA": "Valencia",
    
    "VILLARREAL": "Villarreal",
    
    "GIRONA": "Girona",
    
    "MALLORCA": "Mallorca",
    "RCD MALLORCA": "Mallorca",
    
    "OSASUNA": "Osasuna",
    "CA OSASUNA": "Osasuna",
    
    "ALBACETE": "Albacete",
    "BP": "Burgos",
    "BURGOS": "Burgos",
    "CARTAGENA": "Cartagena",
    "EIBAR": "Eibar",
    "GRANADA": "Granada",
    "HUESCA": "Huesca",
    "LEVANTE": "Levante",
    "TENERIFE": "Tenerife",
}

def normalize_team_name(name: str) -> str:
    """
    Normaliza el nombre de un equipo para facilitar comparaciones.
    Devuelve el nombre estandarizado (Title Case, sin acentos).
    """
    if not name:
        return ""
    
    # 1. Limpieza inicial
    name = str(name).strip()
    
    # 2. Convertir a mayúsculas y quitar acentos normalizando
    upper_no_accents = remove_accents(name).upper()
    
    # 3. Buscar en el mapeo directo
    if upper_no_accents in TEAM_NAME_MAPPINGS:
        return TEAM_NAME_MAPPINGS[upper_no_accents]
    
    # 4. Manejo de prefijos comunes si no se encontró
    prefixes = ["C.A. ", "UD ", "CD ", "SD ", "RCD ", "RC ", "CF ", "FC "]
    for prefix in prefixes:
        if upper_no_accents.startswith(prefix):
            without_prefix = upper_no_accents[len(prefix):].strip()
            if without_prefix in TEAM_NAME_MAPPINGS:
                return TEAM_NAME_MAPPINGS[without_prefix]
            # Si no está en mapa, devolver limpio
            return without_prefix.title()
            
    # 5. Si no hay mapeo específico, devolver versión limpia Title Case
    return remove_accents(name).title()
