from pathlib import Path
from bs4 import BeautifulSoup
import unicodedata
from src.scrapers.base import BaseScraper
from src.utils.normalizers import normalize_team_name

class QuinielaHtmlParser(BaseScraper):
    """
    A scraper to parse the quiniela HTML file and extract match information.
    """

    def __init__(self, html_path: Path):
        """
        Initializes the QuinielaHtmlParser.

        Args:
            html_path (Path): The path to the quiniela HTML file.
        """
        if not html_path.is_file():
            raise FileNotFoundError(f"The specified HTML file does not exist: {html_path}")
        self.html_path = html_path
        super().__init__(str(html_path))

    def _parse_html(self):
        """
        Parses the HTML content of the file.
        """
        with open(self.html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        return BeautifulSoup(html_content, 'html.parser')

    def fetch(self):
        """
        Extracts match data from the parsed HTML.

        Returns:
            list: A list of dictionaries, where each dictionary represents a match
                  with its details.
        """
        soup = self._parse_html()
        partidos = []
        
        partidos_divs = soup.find_all('div', class_='c-caja_base__partido')
        
        for partido_div in partidos_divs:
            try:
                numero_elem = partido_div.find('span', class_='c-equipos__number')
                if not numero_elem:
                    continue
                numero = numero_elem.text.strip()
                
                equipos_elem = partido_div.find('span', class_='c-equipos__teams')
                if not equipos_elem:
                    continue
                
                aria_label = equipos_elem.get('aria-label', '')
                if ' contra ' in aria_label:
                    partes = aria_label.split(' contra ')
                    equipo_local = partes[0].strip()
                    equipo_visitante = partes[1].strip()
                else:
                    data_short = equipos_elem.get('data-short', '')
                    if ' - ' in data_short:
                        partes = data_short.split(' - ')
                        equipo_local = partes[0].strip()
                        equipo_visitante = partes[1].strip()
                    else:
                        continue
                
                horario_elem = partido_div.find('div', class_='c-marcador-horario__time')
                horario = horario_elem.text.strip() if horario_elem else 'Hora no disponible'
                
                partidos.append({
                    'numero': numero,
                    'equipo_local': equipo_local,
                    'equipo_visitante': equipo_visitante,
                    'equipo_local_normalizado': normalize_team_name(equipo_local),
                    'equipo_visitante_normalizado': normalize_team_name(equipo_visitante),
                    'horario': horario
                })
            except Exception as e:
                self.logger.error(f"Error processing a match: {e}")
                continue
        
        return partidos
    
    def parse(self, raw_data):
        return raw_data

    def run(self):
        """Executes the scraper complete."""
        self.logger.info(f"Iniciando {self.name}")
        raw = self.fetch()
        parsed = self.parse(raw)
        self.logger.info(f"Completado: {len(parsed)} items")
        return parsed
