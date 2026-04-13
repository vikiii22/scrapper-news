#!/usr/bin/env python3
"""
ejemplo_uso.py - Ejemplos de uso del sistema Quiniela Pro
"""

from quiniela_pro import QuinielaPro, CONFIG, TEAM_NAME_MAPPING


def ejemplo_basico():
    """Uso básico sin ajustes"""
    print("=" * 80)
    print("EJEMPLO 1: Uso Básico".center(80))
    print("=" * 80 + "\n")
    
    quiniela = QuinielaPro(CONFIG, TEAM_NAME_MAPPING)
    quiniela.run(force_download=False)


def ejemplo_con_champions():
    """Aplicando penalización por Champions League"""
    print("\n" + "=" * 80)
    print("EJEMPLO 2: Ajuste por Champions League".center(80))
    print("=" * 80 + "\n")
    
    # Equipos que jugaron Champions esta semana (cansancio)
    european_adjustments = {
        'Barcelona': -0.10,      # -10% ataque
        'Real Madrid': -0.08,    # -8% ataque
        'Ath Madrid': -0.05,     # -5% ataque
        'Sevilla': -0.06,        # -6% ataque
    }
    
    quiniela = QuinielaPro(CONFIG, TEAM_NAME_MAPPING)
    quiniela.run(
        force_download=False,
        european_adjustments=european_adjustments
    )


def ejemplo_actualizar_datos():
    """Forzar descarga de datos frescos"""
    print("\n" + "=" * 80)
    print("EJEMPLO 3: Actualizar Datos del Servidor".center(80))
    print("=" * 80 + "\n")
    
    quiniela = QuinielaPro(CONFIG, TEAM_NAME_MAPPING)
    quiniela.run(force_download=True)


def ejemplo_configuracion_personalizada():
    """Usar configuración personalizada"""
    print("\n" + "=" * 80)
    print("EJEMPLO 4: Configuración Personalizada".center(80))
    print("=" * 80 + "\n")
    
    # Crear configuración custom
    custom_config = CONFIG.copy()
    custom_config['num_picks'] = 10        # Seleccionar 10 partidos en vez de 8
    custom_config['decay_factor'] = 0.90   # Decaimiento más agresivo
    custom_config['draw_boost'] = 1.15     # +15% boost en empates
    
    quiniela = QuinielaPro(custom_config, TEAM_NAME_MAPPING)
    quiniela.run(force_download=False)


def ejemplo_solo_favoritos():
    """Seleccionar solo los 5 partidos más seguros"""
    print("\n" + "=" * 80)
    print("EJEMPLO 5: Solo Top 5 Favoritos".center(80))
    print("=" * 80 + "\n")
    
    custom_config = CONFIG.copy()
    custom_config['num_picks'] = 5
    
    quiniela = QuinielaPro(custom_config, TEAM_NAME_MAPPING)
    quiniela.run(force_download=False)


if __name__ == "__main__":
    import sys
    
    ejemplos = {
        '1': ('Uso básico', ejemplo_basico),
        '2': ('Ajuste por Champions', ejemplo_con_champions),
        '3': ('Actualizar datos', ejemplo_actualizar_datos),
        '4': ('Configuración custom', ejemplo_configuracion_personalizada),
        '5': ('Solo top 5', ejemplo_solo_favoritos),
    }
    
    if len(sys.argv) > 1:
        ejemplo_num = sys.argv[1]
        if ejemplo_num in ejemplos:
            nombre, funcion = ejemplos[ejemplo_num]
            funcion()
        else:
            print(f"Ejemplo '{ejemplo_num}' no encontrado")
            print("\nEjemplos disponibles:")
            for num, (nombre, _) in ejemplos.items():
                print(f"  {num}: {nombre}")
    else:
        # Si no se especifica, ejecutar el básico
        ejemplo_basico()
        
        print("\n" + "=" * 80)
        print("OTROS EJEMPLOS DISPONIBLES".center(80))
        print("=" * 80)
        print("\nPara ejecutar otros ejemplos, usa:")
        for num, (nombre, _) in ejemplos.items():
            print(f"  python ejemplo_uso.py {num}  # {nombre}")
