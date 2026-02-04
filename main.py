#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script principal que orquesta todos los scrapers y análisis de noticias deportivas
Ejecuta los procesos en el orden correcto para obtener datos y generar predicciones
"""

import subprocess
import sys
import json
import os
from pathlib import Path
from datetime import datetime

# Configurar UTF-8 para Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


class ScraperManager:
    """Gestor centralizado de todos los scrapers del proyecto"""
    
    def __init__(self):
        self.base_dir = Path(__file__).resolve().parent
        self.scraper_dir = self.base_dir / 'scrapper'
        self.data_dir = self.base_dir / 'data'
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.resultados = {
            'fecha_ejecucion': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'procesos': []
        }
    
    def ejecutar_script(self, script_name, descripcion, timeout=300):
        """
        Ejecuta un script de scraping
        
        Args:
            script_name: Nombre del archivo Python a ejecutar
            descripcion: Descripción del proceso para mostrar en consola
            timeout: Tiempo máximo de ejecución en segundos
        
        Returns:
            bool: True si se ejecutó correctamente, False en caso contrario
        """
        print("\n" + "="*80)
        print(f"[{len(self.resultados['procesos']) + 1}] {descripcion}")
        print("="*80)
        
        script_path = self.scraper_dir / script_name
        
        if not script_path.exists():
            print(f"[ERROR] No se encontro el script: {script_path}")
            self.resultados['procesos'].append({
                'nombre': descripcion,
                'script': script_name,
                'estado': 'ERROR',
                'razon': 'Archivo no encontrado'
            })
            return False
        
        try:
            # NO capturar la salida para permitir caracteres especiales
            result = subprocess.run(
                [sys.executable, str(script_path)],
                timeout=timeout
            )
            
            if result.returncode == 0:
                print(f"\n[OK] {descripcion} completado exitosamente")
                self.resultados['procesos'].append({
                    'nombre': descripcion,
                    'script': script_name,
                    'estado': 'COMPLETADO',
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
                return True
            else:
                print(f"\n[FALLO] Error en {descripcion} (codigo {result.returncode})")
                self.resultados['procesos'].append({
                    'nombre': descripcion,
                    'script': script_name,
                    'estado': 'ERROR',
                    'razon': 'El script retorno codigo de error'
                })
                return False
                
        except subprocess.TimeoutExpired:
            print(f"[TIMEOUT] Timeout en {descripcion} (maximo {timeout}s)")
            self.resultados['procesos'].append({
                'nombre': descripcion,
                'script': script_name,
                'estado': 'TIMEOUT',
                'razon': f'Excedio tiempo maximo de {timeout}s'
            })
            return False
        except Exception as e:
            print(f"[ERROR] Error ejecutando {descripcion}: {str(e)}")
            self.resultados['procesos'].append({
                'nombre': descripcion,
                'script': script_name,
                'estado': 'ERROR',
                'razon': str(e)
            })
            return False
    
    def verificar_archivos_datos(self):
        """Verifica que existan los archivos de datos necesarios"""
        archivos_requeridos = [
            'esp_la_liga_resultados.json',
            'segunda_division_completo.json',
            'analisis_futbol_espanol.json'
        ]
        
        print("\n" + "="*80)
        print("VERIFICANDO ARCHIVOS DE DATOS")
        print("="*80)
        
        archivos_encontrados = []
        for archivo in archivos_requeridos:
            ruta = self.data_dir / archivo
            existe = ruta.exists()
            simbolo = "[OK]" if existe else "[NO]"
            print(f"{simbolo} {archivo}")
            if existe:
                archivos_encontrados.append(archivo)
        
        return len(archivos_encontrados) == len(archivos_requeridos)
    
    def ejecutar_pipeline_completo(self):
        """
        Ejecuta el pipeline completo en el orden correcto:
        1. SoccerData Scraper (Primera División)
        2. Segunda División Scraper
        3. Análisis de Fútbol Español (combina datos y genera predicciones)
        4. Quiniela Analysis (genera apuestas basadas en predicciones)
        """
        
        print("\n" + "="*80)
        print("SPORTS NEWS SCRAPER - PIPELINE COMPLETO".center(80))
        print(f"Iniciado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}".center(80))
        print("="*80)
        
        # Paso 1: SoccerData Scraper (Primera División)
        resultado_1 = self.ejecutar_script(
            'scrapper-soccerdata.py',
            'SoccerData Scraper - Primera Division (La Liga)',
            timeout=300
        )
        
        if not resultado_1:
            print("\n[ADVERTENCIA] Primera Division no se completo, continuando...")
        
        # Paso 2: Segunda División Scraper
        resultado_2 = self.ejecutar_script(
            'scrapper-segunda-division.py',
            'Segunda Division Scraper',
            timeout=300
        )
        
        if not resultado_2:
            print("\n[ADVERTENCIA] Segunda Division no se completo, continuando...")
        
        # Paso 3: Análisis de Fútbol Español
        resultado_3 = self.ejecutar_script(
            'scrapper-futbol-espanol.py',
            'Analisis de Futbol Espanol (Predicciones)',
            timeout=600
        )
        
        if not resultado_3:
            print("\n[ADVERTENCIA] Analisis de Futbol no se completo, continuando...")
        
        # Paso 4: Quiniela Analysis
        resultado_4 = self.ejecutar_script(
            'quiniela_analysis.py',
            'Quiniela Analysis (Apuestas Recomendadas)',
            timeout=300
        )
        
        if not resultado_4:
            print("\n[ADVERTENCIA] Quiniela Analysis no se completo")
        
        # Resumen final
        self.mostrar_resumen_final(resultado_1, resultado_2, resultado_3, resultado_4)
    
    def mostrar_resumen_final(self, r1, r2, r3, r4):
        """Muestra un resumen final de la ejecución"""
        
        print("\n" + "="*80)
        print("RESUMEN DE EJECUCION".center(80))
        print("="*80)
        
        estado_icono = {True: "[OK]", False: "[FALLO]"}
        
        print(f"\n{estado_icono[r1]} Paso 1 - SoccerData Scraper (Primera Division)")
        print(f"{estado_icono[r2]} Paso 2 - Segunda Division Scraper")
        print(f"{estado_icono[r3]} Paso 3 - Analisis de Futbol Espanol")
        print(f"{estado_icono[r4]} Paso 4 - Quiniela Analysis")
        
        # Verificar archivos generados
        print("\n" + "-"*80)
        print("ARCHIVOS GENERADOS:")
        print("-"*80)
        
        archivos_esperados = {
            'esp_la_liga_resultados.json': 'Primera Division (La Liga)',
            'segunda_division_completo.json': 'Segunda Division',
            'analisis_futbol_espanol.json': 'Analisis y Predicciones',
            'apuestas_quiniela.json': 'Apuestas Quiniela',
            'predicciones_proxima_jornada.json': 'Predicciones Proxima Jornada'
        }
        
        archivos_encontrados = 0
        for archivo, descripcion in archivos_esperados.items():
            ruta = self.data_dir / archivo
            existe = ruta.exists()
            if existe:
                archivos_encontrados += 1
                tamano = ruta.stat().st_size / 1024
                print(f"  [OK] {archivo:<35} ({tamano:.1f} KB) - {descripcion}")
            else:
                print(f"  [NO] {archivo:<35} NO ENCONTRADO")
        
        print(f"\nArchivos encontrados: {archivos_encontrados}/{len(archivos_esperados)}")
        
        # Resumen general
        procesos_completados = sum(1 for p in self.resultados['procesos'] if p['estado'] == 'COMPLETADO')
        procesos_totales = len(self.resultados['procesos'])
        
        print("\n" + "-"*80)
        print("ESTADISTICAS:")
        print("-"*80)
        print(f"  Procesos completados: {procesos_completados}/{procesos_totales}")
        print(f"  Inicio: {self.resultados['fecha_ejecucion']}")
        print(f"  Fin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Guardar resumen en JSON
        self.resultados['resumen'] = {
            'procesos_completados': procesos_completados,
            'procesos_totales': procesos_totales,
            'exito_general': procesos_completados == procesos_totales,
            'archivos_generados': archivos_encontrados
        }
        
        resultado_path = self.data_dir / 'ejecucion_resumen.json'
        with open(resultado_path, 'w', encoding='utf-8') as f:
            json.dump(self.resultados, f, ensure_ascii=False, indent=2)
        
        print(f"\n[OK] Resumen guardado en: {resultado_path}")
        
        print("\n" + "="*80)
        if procesos_completados == procesos_totales:
            print("PROCESO COMPLETADO EXITOSAMENTE!".center(80))
        else:
            print(f"PROCESO COMPLETADO CON {procesos_totales - procesos_completados} ERRORES".center(80))
        print("="*80 + "\n")
        
        # Mostrar próximos pasos
        print("PROXIMOS PASOS:")
        print("-"*80)
        print("1. Revisar los archivos JSON generados en la carpeta 'data/'")
        print("2. Ver predicciones en: analisis_futbol_espanol.json")
        print("3. Ver apuestas quiniela en: apuestas_quiniela.json")
        print("4. Ejecutar nuevamente cuando se jueguen los partidos para obtener resultados reales")
        print("5. Comparar predicciones vs resultados para mejorar el modelo")
        print()


def main():
    """Función principal"""
    manager = ScraperManager()
    
    try:
        manager.ejecutar_pipeline_completo()
        
    except KeyboardInterrupt:
        print("\n\n[INTERRUMPIDO] Proceso interrumpido por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n[ERROR CRITICO] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
