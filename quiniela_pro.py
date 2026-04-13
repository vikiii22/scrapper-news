#!/usr/bin/env python3
"""
quiniela_pro.py - Sistema profesional de predicción para Quiniela española
Autor: Senior Python Developer & Data Scientist
Versión: 1.0.0
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import warnings

import requests
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
from scipy.stats import poisson
from tabulate import tabulate

warnings.filterwarnings('ignore')


# ============================================================================
# CONFIGURACIÓN Y CONSTANTES
# ============================================================================

CONFIG = {
    'data_url_base': 'https://www.football-data.co.uk/mmz4281/2526/',
    'losilla_url': 'https://www.eduardolosilla.es/',
    'csv_files': ['SP1.csv', 'SP2.csv'],
    'data_dir': 'data',
    'output_file': 'jornada_prediccion.csv',
    'decay_factor': 0.95,  # Factor de decaimiento exponencial (partidos más recientes pesan más)
    'draw_boost': 1.10,    # +10% probabilidad de empate en partidos equilibrados
    'low_xg_threshold': 2.0,  # Umbral de xG combinado para considerar bajo
    'num_picks': 8,        # Número de partidos a seleccionar
}

# Diccionario de mapeo de nombres de equipos
TEAM_NAME_MAPPING = {
    'AT.MADRID': 'Ath Madrid',
    'ATH.MADRID': 'Ath Madrid',
    'ATLETICO': 'Ath Madrid',
    'ATH MADRID': 'Ath Madrid',
    'ATHLETIC': 'Ath Bilbao',
    'ATH.BILBAO': 'Ath Bilbao',
    'ATH BILBAO': 'Ath Bilbao',
    'BARCELONA': 'Barcelona',
    'BARÇA': 'Barcelona',
    'R.MADRID': 'Real Madrid',
    'REAL MADRID': 'Real Madrid',
    'REAL M.': 'Real Madrid',
    'SEVILLA': 'Sevilla',
    'VILLARREAL': 'Villarreal',
    'VALENCIA': 'Valencia',
    'BETIS': 'Betis',
    'R.BETIS': 'Betis',
    'REAL BETIS': 'Betis',
    'R.SOCIEDAD': 'Sociedad',
    'REAL SOCIEDAD': 'Sociedad',
    'LA REAL': 'Sociedad',
    'OSASUNA': 'Osasuna',
    'CELTA': 'Celta',
    'ESPANYOL': 'Espanol',
    'ESPAÑOL': 'Espanol',
    'GETAFE': 'Getafe',
    'GIRONA': 'Girona',
    'MALLORCA': 'Mallorca',
    'RAYO': 'Vallecano',
    'RAYO VALLECANO': 'Vallecano',
    'VALLADOLID': 'Valladolid',
    'ALMERIA': 'Almeria',
    'ALMERÍA': 'Almeria',
    'CADIZ': 'Cadiz',
    'CÁDIZ': 'Cadiz',
    'ELCHE': 'Elche',
    'ALAVES': 'Alaves',
    'ALAVÉS': 'Alaves',
    'LEGANES': 'Leganes',
    'LEGANÉS': 'Leganes',
    'LAS PALMAS': 'Las Palmas',
}


# ============================================================================
# CLASES DE DATOS
# ============================================================================

@dataclass
class Match:
    """Representa un partido de la jornada"""
    home_team: str
    away_team: str
    home_prob: float = 0.0
    draw_prob: float = 0.0
    away_prob: float = 0.0
    prediction: str = ''
    confidence: float = 0.0
    entropy: float = 0.0


@dataclass
class TeamStats:
    """Estadísticas de un equipo"""
    attack_strength: float
    defense_strength: float
    home_advantage: float = 1.0


# ============================================================================
# CLASE: DataDownloader (Responsabilidad: Descarga de datos)
# ============================================================================

class DataDownloader:
    """Gestiona la descarga de archivos CSV desde football-data.co.uk"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.data_dir = Path(config['data_dir'])
        self.data_dir.mkdir(exist_ok=True)
    
    def download_file(self, filename: str, force: bool = False) -> Path:
        """
        Descarga un archivo CSV si no existe o si se fuerza la descarga
        
        Args:
            filename: Nombre del archivo a descargar
            force: Si True, descarga incluso si existe
            
        Returns:
            Path al archivo descargado
        """
        file_path = self.data_dir / filename
        
        if file_path.exists() and not force:
            print(f"✓ {filename} ya existe localmente")
            return file_path
        
        url = f"{self.config['data_url_base']}{filename}"
        
        try:
            print(f"⬇ Descargando {filename}...")
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            print(f"✓ {filename} descargado correctamente")
            return file_path
            
        except requests.RequestException as e:
            print(f"✗ Error descargando {filename}: {e}")
            raise
    
    def download_all(self, force: bool = False) -> List[Path]:
        """Descarga todos los archivos CSV configurados"""
        return [self.download_file(f, force) for f in self.config['csv_files']]


# ============================================================================
# CLASE: LosillaParser (Responsabilidad: Web Scraping)
# ============================================================================

class LosillaParser:
    """Extrae los partidos de la jornada desde eduardolosilla.es"""
    
    def __init__(self, url: str, team_mapping: Dict[str, str]):
        self.url = url
        self.team_mapping = team_mapping
    
    def normalize_team_name(self, raw_name: str) -> str:
        """
        Normaliza el nombre de un equipo usando el diccionario de mapeo
        
        Args:
            raw_name: Nombre crudo del equipo
            
        Returns:
            Nombre normalizado
        """
        clean_name = raw_name.strip().upper()
        return self.team_mapping.get(clean_name, raw_name.strip())
    
    def parse_matches(self) -> List[Match]:
        """
        Extrae los 15 partidos de la jornada actual
        
        Returns:
            Lista de objetos Match
        """
        try:
            print(f"🌐 Scrapeando partidos desde {self.url}...")
            
            response = requests.get(self.url, timeout=30, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            matches = []
            
            # Estrategia 1: Buscar tabla de partidos
            table = soup.find('table', class_=lambda x: x and 'partidos' in x.lower() if x else False)
            
            if not table:
                # Estrategia 2: Buscar por estructura común de Losilla
                table = soup.find('table')
            
            if not table:
                # Estrategia 3: Buscar divs con partidos
                match_divs = soup.find_all('div', class_=lambda x: x and 'partido' in x.lower() if x else False)
                
                for div in match_divs[:15]:
                    text = div.get_text(separator=' ', strip=True)
                    # Buscar patrón: "Equipo1 - Equipo2" o "Equipo1 vs Equipo2"
                    parts = text.split('-') if '-' in text else text.split('vs')
                    
                    if len(parts) == 2:
                        home = self.normalize_team_name(parts[0])
                        away = self.normalize_team_name(parts[1])
                        matches.append(Match(home_team=home, away_team=away))
            else:
                # Parsear tabla
                rows = table.find_all('tr')[1:]  # Saltar encabezado
                
                for row in rows[:15]:
                    cols = row.find_all('td')
                    if len(cols) >= 2:
                        home = self.normalize_team_name(cols[0].get_text(strip=True))
                        away = self.normalize_team_name(cols[-1].get_text(strip=True))
                        matches.append(Match(home_team=home, away_team=away))
            
            if len(matches) == 0:
                print("⚠ No se encontraron partidos. Usando partidos de ejemplo.")
                # Fallback: partidos de ejemplo
                matches = self._get_fallback_matches()
            
            print(f"✓ {len(matches)} partidos extraídos correctamente")
            return matches
            
        except Exception as e:
            print(f"⚠ Error en scraping: {e}")
            print("⚠ Usando partidos de ejemplo como fallback")
            return self._get_fallback_matches()
    
    def _get_fallback_matches(self) -> List[Match]:
        """Partidos de ejemplo en caso de fallo en el scraping"""
        example_matches = [
            ('Barcelona', 'Real Madrid'),
            ('Ath Madrid', 'Sevilla'),
            ('Villarreal', 'Betis'),
            ('Sociedad', 'Ath Bilbao'),
            ('Valencia', 'Celta'),
            ('Getafe', 'Osasuna'),
            ('Mallorca', 'Girona'),
            ('Vallecano', 'Espanol'),
            ('Las Palmas', 'Alaves'),
            ('Leganes', 'Valladolid'),
            ('Cadiz', 'Almeria'),
            ('Betis', 'Valencia'),
            ('Sevilla', 'Mallorca'),
            ('Real Madrid', 'Getafe'),
            ('Barcelona', 'Celta'),
        ]
        return [Match(home_team=h, away_team=a) for h, a in example_matches[:15]]


# ============================================================================
# CLASE: StatisticalModel (Responsabilidad: Modelo estadístico)
# ============================================================================

class StatisticalModel:
    """
    Modelo estadístico avanzado basado en Poisson + Dixon-Coles
    con time-weighting y ajustes por competición europea
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.team_stats: Dict[str, TeamStats] = {}
        self.league_avg_goals = 1.5
        self.european_adjustments: Dict[str, float] = {}
    
    def load_historical_data(self, csv_paths: List[Path]) -> pd.DataFrame:
        """Carga y combina datos históricos de los CSV"""
        dfs = []
        
        for path in csv_paths:
            try:
                df = pd.read_csv(path, encoding='latin-1')
                dfs.append(df)
                print(f"✓ Cargados {len(df)} registros desde {path.name}")
            except Exception as e:
                print(f"⚠ Error cargando {path}: {e}")
        
        if not dfs:
            raise ValueError("No se pudo cargar ningún archivo CSV")
        
        combined = pd.concat(dfs, ignore_index=True)
        
        # Limpiar datos
        combined = combined.dropna(subset=['HomeTeam', 'AwayTeam', 'FTHG', 'FTAG'])
        combined['Date'] = pd.to_datetime(combined.get('Date', datetime.now()), errors='coerce')
        
        return combined.sort_values('Date', ascending=False).reset_index(drop=True)
    
    def calculate_team_strengths(self, data: pd.DataFrame):
        """
        Calcula la fuerza de ataque y defensa de cada equipo
        aplicando time-weighting (decaimiento exponencial)
        """
        print("📊 Calculando fuerzas de ataque y defensa con time-weighting...")
        
        # Calcular promedio de goles de la liga
        self.league_avg_goals = (data['FTHG'].mean() + data['FTAG'].mean()) / 2
        
        # Aplicar pesos exponenciales (partidos recientes pesan más)
        data['weight'] = self.config['decay_factor'] ** np.arange(len(data))
        
        teams = set(data['HomeTeam'].unique()) | set(data['AwayTeam'].unique())
        
        for team in teams:
            # Partidos como local
            home_matches = data[data['HomeTeam'] == team].copy()
            home_goals_scored = (home_matches['FTHG'] * home_matches['weight']).sum()
            home_goals_conceded = (home_matches['FTAG'] * home_matches['weight']).sum()
            home_weight_sum = home_matches['weight'].sum()
            
            # Partidos como visitante
            away_matches = data[data['AwayTeam'] == team].copy()
            away_goals_scored = (away_matches['FTAG'] * away_matches['weight']).sum()
            away_goals_conceded = (away_matches['FTHG'] * away_matches['weight']).sum()
            away_weight_sum = away_matches['weight'].sum()
            
            total_weight = home_weight_sum + away_weight_sum
            
            if total_weight > 0:
                # Fuerza de ataque normalizada
                avg_goals_scored = (home_goals_scored + away_goals_scored) / total_weight
                attack_strength = avg_goals_scored / self.league_avg_goals
                
                # Fuerza defensiva normalizada (inversa: menor es mejor)
                avg_goals_conceded = (home_goals_conceded + away_goals_conceded) / total_weight
                defense_strength = avg_goals_conceded / self.league_avg_goals
                
                # Ventaja de jugar en casa
                home_advantage = 1.2 if home_weight_sum > 0 else 1.0
                
                self.team_stats[team] = TeamStats(
                    attack_strength=attack_strength,
                    defense_strength=defense_strength,
                    home_advantage=home_advantage
                )
        
        print(f"✓ Estadísticas calculadas para {len(self.team_stats)} equipos")
    
    def set_european_adjustments(self, adjustments: Dict[str, float]):
        """
        Establece ajustes manuales por cansancio de competición europea
        
        Args:
            adjustments: Dict con formato {'Barcelona': -0.10, 'Real Madrid': -0.08}
                        (valores negativos reducen el ataque)
        """
        self.european_adjustments = adjustments
        print(f"⚙ Ajustes europeos aplicados: {adjustments}")
    
    def dixon_coles_correction(self, home_goals: int, away_goals: int, 
                               lambda_home: float, lambda_away: float) -> float:
        """
        Factor de corrección Dixon-Coles para resultados de empate
        Aumenta la probabilidad de empates en partidos equilibrados
        """
        tau = 0.1  # Parámetro de ajuste Dixon-Coles
        
        if home_goals == 0 and away_goals == 0:
            return 1 - lambda_home * lambda_away * tau
        elif home_goals == 0 and away_goals == 1:
            return 1 + lambda_home * tau
        elif home_goals == 1 and away_goals == 0:
            return 1 + lambda_away * tau
        elif home_goals == 1 and away_goals == 1:
            return 1 - tau
        else:
            return 1.0
    
    def predict_match(self, match: Match) -> Match:
        """
        Predice el resultado de un partido usando Poisson + Dixon-Coles
        
        Args:
            match: Objeto Match con equipos local y visitante
            
        Returns:
            Match actualizado con probabilidades y predicción
        """
        home_stats = self.team_stats.get(match.home_team)
        away_stats = self.team_stats.get(match.away_team)
        
        if not home_stats or not away_stats:
            # Si no hay datos, asignar probabilidades equiprobables
            match.home_prob = match.draw_prob = match.away_prob = 0.33
            match.prediction = 'X'
            match.confidence = 0.33
            match.entropy = self._calculate_entropy([0.33, 0.33, 0.33])
            return match
        
        # Aplicar ajustes por competición europea
        home_attack_adj = 1.0 + self.european_adjustments.get(match.home_team, 0.0)
        away_attack_adj = 1.0 + self.european_adjustments.get(match.away_team, 0.0)
        
        # Calcular expected goals (lambda) usando el modelo de Poisson
        lambda_home = (
            home_stats.attack_strength * home_attack_adj *
            away_stats.defense_strength *
            home_stats.home_advantage *
            self.league_avg_goals
        )
        
        lambda_away = (
            away_stats.attack_strength * away_attack_adj *
            home_stats.defense_strength *
            self.league_avg_goals
        )
        
        # Calcular matriz de probabilidades para todos los resultados posibles
        max_goals = 6
        prob_matrix = np.zeros((max_goals + 1, max_goals + 1))
        
        for i in range(max_goals + 1):
            for j in range(max_goals + 1):
                prob_poisson = poisson.pmf(i, lambda_home) * poisson.pmf(j, lambda_away)
                correction = self.dixon_coles_correction(i, j, lambda_home, lambda_away)
                prob_matrix[i, j] = prob_poisson * correction
        
        # Normalizar probabilidades
        prob_matrix = prob_matrix / prob_matrix.sum()
        
        # Calcular probabilidades 1, X, 2
        home_win_prob = np.tril(prob_matrix, -1).sum()  # Home > Away
        draw_prob = np.trace(prob_matrix)               # Home == Away
        away_win_prob = np.triu(prob_matrix, 1).sum()   # Home < Away
        
        # Boost de empate para partidos con xG bajo (equilibrados)
        total_xg = lambda_home + lambda_away
        if total_xg < self.config['low_xg_threshold']:
            boost = self.config['draw_boost']
            draw_prob *= boost
            # Renormalizar
            total = home_win_prob + draw_prob + away_win_prob
            home_win_prob /= total
            draw_prob /= total
            away_win_prob /= total
        
        match.home_prob = home_win_prob
        match.draw_prob = draw_prob
        match.away_prob = away_win_prob
        
        # Determinar predicción (máxima probabilidad)
        probs = {'1': home_win_prob, 'X': draw_prob, '2': away_win_prob}
        match.prediction = max(probs, key=probs.get)
        match.confidence = max(probs.values())
        
        # Calcular entropía (menor entropía = mayor certeza)
        match.entropy = self._calculate_entropy([home_win_prob, draw_prob, away_win_prob])
        
        return match
    
    def _calculate_entropy(self, probabilities: List[float]) -> float:
        """Calcula la entropía de Shannon para medir incertidumbre"""
        entropy = 0.0
        for p in probabilities:
            if p > 0:
                entropy -= p * np.log2(p)
        return entropy


# ============================================================================
# CLASE: BettingStrategy (Responsabilidad: Lógica de apuesta)
# ============================================================================

class BettingStrategy:
    """Determina qué partidos apostar basándose en menor entropía"""
    
    def __init__(self, num_picks: int):
        self.num_picks = num_picks
    
    def select_best_matches(self, matches: List[Match]) -> List[Match]:
        """
        Selecciona los N partidos con menor entropía (mayor certeza)
        
        Args:
            matches: Lista de partidos con predicciones
            
        Returns:
            Lista ordenada de los mejores N partidos
        """
        # Ordenar por entropía ascendente (menor entropía = más certeza)
        sorted_matches = sorted(matches, key=lambda m: m.entropy)
        
        # Seleccionar los N mejores
        best_matches = sorted_matches[:self.num_picks]
        
        print(f"✓ Seleccionados {len(best_matches)} partidos con mayor certeza")
        return best_matches


# ============================================================================
# CLASE: OutputFormatter (Responsabilidad: Formatear salida)
# ============================================================================

class OutputFormatter:
    """Formatea y guarda los resultados"""
    
    @staticmethod
    def print_table(matches: List[Match], title: str = "PREDICCIONES"):
        """Muestra tabla formateada en terminal"""
        print(f"\n{'=' * 80}")
        print(f"{title:^80}")
        print(f"{'=' * 80}\n")
        
        table_data = []
        for i, m in enumerate(matches, 1):
            table_data.append([
                i,
                f"{m.home_team} vs {m.away_team}",
                m.prediction,
                f"{m.home_prob:.1%}",
                f"{m.draw_prob:.1%}",
                f"{m.away_prob:.1%}",
                f"{m.confidence:.1%}",
                f"{m.entropy:.3f}"
            ])
        
        headers = ['#', 'Partido', 'Pred', 'Prob 1', 'Prob X', 'Prob 2', 'Conf', 'Entropía']
        print(tabulate(table_data, headers=headers, tablefmt='grid'))
    
    @staticmethod
    def save_csv(matches: List[Match], filename: str):
        """Guarda predicciones en CSV"""
        data = []
        for m in matches:
            data.append({
                'Equipo_Local': m.home_team,
                'Equipo_Visitante': m.away_team,
                'Prediccion': m.prediction,
                'Prob_1': f"{m.home_prob:.4f}",
                'Prob_X': f"{m.draw_prob:.4f}",
                'Prob_2': f"{m.away_prob:.4f}",
                'Confianza': f"{m.confidence:.4f}",
                'Entropia': f"{m.entropy:.4f}",
            })
        
        df = pd.DataFrame(data)
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"\n✓ Resultados guardados en: {filename}")


# ============================================================================
# CLASE PRINCIPAL: QuinielaPro (Orquestador)
# ============================================================================

class QuinielaPro:
    """Orquestador principal del sistema de predicción"""
    
    def __init__(self, config: Dict, team_mapping: Dict[str, str]):
        self.config = config
        self.downloader = DataDownloader(config)
        self.parser = LosillaParser(config['losilla_url'], team_mapping)
        self.model = StatisticalModel(config)
        self.strategy = BettingStrategy(config['num_picks'])
        self.formatter = OutputFormatter()
    
    def run(self, force_download: bool = False, 
            european_adjustments: Optional[Dict[str, float]] = None):
        """
        Ejecuta el flujo completo de predicción
        
        Args:
            force_download: Si True, fuerza descarga de archivos
            european_adjustments: Ajustes por competición europea
        """
        print("\n" + "="*80)
        print("🎯 QUINIELA PRO - Sistema Profesional de Predicción".center(80))
        print("="*80 + "\n")
        
        try:
            # 1. Descargar datos históricos
            print("📥 PASO 1: Descarga de datos históricos")
            csv_paths = self.downloader.download_all(force=force_download)
            
            # 2. Cargar y procesar datos históricos
            print("\n📊 PASO 2: Procesamiento de datos históricos")
            historical_data = self.model.load_historical_data(csv_paths)
            self.model.calculate_team_strengths(historical_data)
            
            # 3. Aplicar ajustes por competición europea (si se proporcionan)
            if european_adjustments:
                self.model.set_european_adjustments(european_adjustments)
            
            # 4. Extraer partidos de la jornada actual
            print("\n🌐 PASO 3: Extracción de partidos de la jornada")
            matches = self.parser.parse_matches()
            
            if not matches:
                print("✗ No se pudieron obtener partidos")
                return
            
            # 5. Predecir resultados
            print("\n🔮 PASO 4: Generación de predicciones")
            predicted_matches = []
            for match in matches:
                predicted = self.model.predict_match(match)
                predicted_matches.append(predicted)
            
            # 6. Seleccionar mejores apuestas
            print("\n💎 PASO 5: Selección de mejores apuestas")
            best_picks = self.strategy.select_best_matches(predicted_matches)
            
            # 7. Mostrar resultados
            print("\n📋 PASO 6: Presentación de resultados")
            self.formatter.print_table(best_picks, "TOP 8 APUESTAS RECOMENDADAS")
            self.formatter.print_table(predicted_matches, "TODAS LAS PREDICCIONES")
            
            # 8. Guardar en CSV
            output_file = self.config['output_file']
            self.formatter.save_csv(best_picks, output_file)
            
            print("\n" + "="*80)
            print("✅ PROCESO COMPLETADO EXITOSAMENTE".center(80))
            print("="*80 + "\n")
            
        except Exception as e:
            print(f"\n✗ ERROR CRÍTICO: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


# ============================================================================
# FUNCIÓN PRINCIPAL
# ============================================================================

def main():
    """Punto de entrada principal"""
    
    # Ejemplo de ajustes por competición europea (opcional)
    # Valores negativos reducen el ataque por cansancio
    european_adjustments = {
        # 'Barcelona': -0.10,      # -10% ataque tras Champions
        # 'Real Madrid': -0.08,    # -8% ataque
        # 'Ath Madrid': -0.05,     # -5% ataque
    }
    
    # Crear instancia y ejecutar
    quiniela = QuinielaPro(CONFIG, TEAM_NAME_MAPPING)
    
    # Ejecutar con:
    # - force_download=False: usa archivos locales si existen
    # - force_download=True: descarga archivos incluso si existen
    quiniela.run(
        force_download=False,
        european_adjustments=european_adjustments
    )


if __name__ == "__main__":
    main()
