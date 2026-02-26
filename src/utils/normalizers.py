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

# Mapeo de nombres normalizados (MAYÚSCULAS SIN ACENTOS) a nombre estándar de SofaScore
# La clave debe estar en MAYÚSCULAS y SIN ACENTOS para coincidir con la lógica
# Los VALORES deben coincidir EXACTAMENTE con los nombres que devuelve SofaScore
TEAM_NAME_MAPPINGS = {
    # ─── LA LIGA ──────────────────────────────────────────────────────────────
    "R.MADRID":           "Real Madrid",
    "R. MADRID":          "Real Madrid",
    "REAL MADRID":        "Real Madrid",

    "R.SOCIEDAD":         "Real Sociedad",
    "R. SOCIEDAD":        "Real Sociedad",
    "REAL SOCIEDAD":      "Real Sociedad",

    "ATH.CLUB":           "Athletic Club",
    "ATH. CLUB":          "Athletic Club",
    "ATHLETIC CLUB":      "Athletic Club",
    "ATHLETIC":           "Athletic Club",
    "ATH. BILBAO":        "Athletic Club",
    "ATHLETIC BILBAO":    "Athletic Club",

    "ATL.MADRID":         "Atlético Madrid",
    "ATL. MADRID":        "Atlético Madrid",
    "AT.MADRID":          "Atlético Madrid",
    "ATLETICO MADRID":    "Atlético Madrid",
    "ATLETICO DE MADRID": "Atlético Madrid",
    "ATLETICO":           "Atlético Madrid",

    "BARCELONA":          "Barcelona",
    "FC BARCELONA":       "Barcelona",
    "BARCA":              "Barcelona",

    "SEVILLA":            "Sevilla",
    "FC SEVILLA":         "Sevilla",

    "VALENCIA":           "Valencia",
    "FC VALENCIA":        "Valencia",

    "VILLARREAL":         "Villarreal",
    "VILLARREAL CF":      "Villarreal",

    "GIRONA":             "Girona FC",
    "GIRONA FC":          "Girona FC",

    "MALLORCA":           "Mallorca",
    "RCD MALLORCA":       "Mallorca",

    "OSASUNA":            "Osasuna",
    "CA OSASUNA":         "Osasuna",

    "R.BETIS":            "Real Betis",
    "REAL BETIS":         "Real Betis",
    "BETIS":              "Real Betis",

    "RAYO":               "Rayo Vallecano",
    "RAYO VALLECANO":     "Rayo Vallecano",

    "GETAFE":             "Getafe",
    "GETAFE CF":          "Getafe",

    "CELTA":              "Celta Vigo",
    "RC CELTA":           "Celta Vigo",
    "CELTA DE VIGO":      "Celta Vigo",
    "CELTA VIGO":         "Celta Vigo",

    "ESPANYOL":           "Espanyol",
    "RCD ESPANYOL":       "Espanyol",
    "ESPANOL":            "Espanyol",

    "ALAVES":             "Deportivo Alavés",
    "DEPORTIVO ALAVES":   "Deportivo Alavés",

    "ELCHE":              "Elche",
    "CF ELCHE":           "Elche",
    "ELCHE CF":           "Elche",

    # ─── SEGUNDA DIVISIÓN ─────────────────────────────────────────────────────
    "R.OVIEDO":           "Real Oviedo",
    "REAL OVIEDO":        "Real Oviedo",

    "R.ZARAGOZA":         "Real Zaragoza",
    "REAL ZARAGOZA":      "Real Zaragoza",
    "ZARAGOZA":           "Real Zaragoza",

    "SP.GIJON":           "Sporting Gijón",
    "SPORTING GIJON":     "Sporting Gijón",
    "SPORTING":           "Sporting Gijón",
    "SPORTING GIJON":     "Sporting Gijón",

    # Cultural Leonesa — La Quiniela la abrevia 'C. LEONESA'
    "C. LEONESA":         "Cultural Leonesa",
    "CULTURAL LEONESA":   "Cultural Leonesa",
    "C.LEONESA":          "Cultural Leonesa",
    "LEONESA":            "Cultural Leonesa",

    "R.RACING C.":        "Real Racing Club",
    "RACING SANTANDER":   "Real Racing Club",
    "RACING":             "Real Racing Club",
    "RACING S.":          "Real Racing Club",
    "REAL RACING CLUB":   "Real Racing Club",

    # Burgos — nombre completo en SofaScore
    "BP":                 "Burgos Club de Fútbol",
    "BURGOS":             "Burgos Club de Fútbol",
    "BURGOS CF":          "Burgos Club de Fútbol",
    "BURGOS CLUB":        "Burgos Club de Fútbol",

    # Castellón — nombre con acento en SofaScore
    "CASTELLON":          "CD Castellón",
    "CD CASTELLON":       "CD Castellón",
    "CD CASTELLAN":       "CD Castellón",

    "ALMERIA":            "Almería",
    "UD ALMERIA":         "Almería",

    "MALAGA":             "Málaga",
    "CF MALAGA":          "Málaga",

    "LEGANES":            "Leganés",
    "LEGANÉS":            "Leganés",
    "CD LEGANES":         "Leganés",

    "MIRANDES":           "Mirandés",

    "CORDOBA":            "Córdoba",
    "CORDOBA CF":         "Córdoba",

    "DEPORTIVO":          "Deportivo La Coruña",
    "RC DEPORTIVO":       "Deportivo La Coruña",
    "DEPORTIVO LA CORUNA": "Deportivo La Coruña",
    "DEPORTIVO LA CORUÑA": "Deportivo La Coruña",

    "CADIZ":              "Cádiz",
    "CADIZ CF":           "Cádiz",

    "ALBACETE":           "Albacete Balompié",
    "ALBACETE BALOMPIE":  "Albacete Balompié",

    "GRANADA":            "Granada",
    "GRANADA CF":         "Granada",

    "HUESCA":             "Huesca",
    "SD HUESCA":          "Huesca",

    "R.VALLADOLID":       "Real Valladolid",
    "REAL VALLADOLID":    "Real Valladolid",
    "VALLADOLID":         "Real Valladolid",

    "ELDENSE":            "Eldense",
    "FERROL":             "Racing Ferrol",
    "RACING FERROL":      "Racing Ferrol",
    "CARTAGENA":          "Cartagena",
    "EIBAR":              "Eibar",
    "LEVANTE":            "Levante",
    "LEVANTE UD":         "Levante",
    "TENERIFE":           "Tenerife",
    "CD TENERIFE":        "Tenerife",
    "ANDORRA":            "FC Andorra",
    "FC ANDORRA":         "FC Andorra",
    "CEUTA":              "AD Ceuta",
    "AD CEUTA":           "AD Ceuta",
    "LAS PALMAS":         "Las Palmas",
    "UD LAS PALMAS":      "Las Palmas",
}

def normalize_team_name(name: str) -> str:
    """
    Normaliza el nombre de un equipo para facilitar comparaciones.
    Devuelve el nombre estandarizado tal como aparece en SofaScore.
    """
    if not name:
        return ""
    
    # 1. Limpieza inicial
    name = str(name).strip()
    
    # INTENTO DIRECO: Buscar tal cual (para casos con encoding roto que tenemos mapeados)
    if name in TEAM_NAME_MAPPINGS:
        return TEAM_NAME_MAPPINGS[name]
        
    # INTENTO UPPER DIRECTO: Buscar en mayusculas sin quitar acentos aun
    if name.upper() in TEAM_NAME_MAPPINGS:
        return TEAM_NAME_MAPPINGS[name.upper()]
    
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
            # Si no está en mapa, devolver el nombre original sin el prefijo
            return name[len(prefix):].strip()
            
    # 5. Si no hay mapeo específico, devolver el nombre original sin procesamiento
    return name
