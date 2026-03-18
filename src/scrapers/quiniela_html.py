from pathlib import Path
from bs4 import BeautifulSoup
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

    def _extract_jornada(self, soup) -> int:
        """Extrae el número de jornada del encabezado HTML (ej: 'JORNADA 48').

        Busca el primer <h3> que contenga la palabra 'JORNADA' y extrae el entero
        que le sigue. Devuelve 0 si no se puede determinar.
        """
        import re
        for tag in soup.find_all(['h3', 'h2', 'h1']):
            text = tag.get_text(strip=True)
            match = re.search(r'JORNADA\s+(\d+)', text, re.IGNORECASE)
            if match:
                return int(match.group(1))
        self.logger.warning("No se pudo extraer el número de jornada del HTML.")
        return 0

    def fetch(self):
        """
        Extracts match data from the parsed HTML.

        Returns:
            list: A list of dictionaries, where each dictionary represents a match
                  with its details.
        """
        soup = self._parse_html()
        partidos = []

        # Extraer número de jornada del encabezado HTML (ej: "JORNADA 48")
        jornada = self._extract_jornada(soup)

        partidos_divs = soup.find_all('div', class_='c-caja_base__partido')
        
        for partido_div in partidos_divs:
            try:
                numero_elem = partido_div.find('span', class_='c-equipos__number')
                if not numero_elem:
                    continue
                numero = int(numero_elem.text.strip())
                
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
                percentages = self._extract_percentages(partido_div)
                
                partidos.append({
                    'numero': numero,
                    'jornada': jornada,  # Campo añadido: número de jornada extraído del header HTML
                    'equipo_local': equipo_local,
                    'equipo_visitante': equipo_visitante,
                    'equipo_local_normalizado': normalize_team_name(equipo_local),
                    'equipo_visitante_normalizado': normalize_team_name(equipo_visitante),
                    'horario': horario,
                    'source_percentages': percentages,
                })
            except Exception as e:
                self.logger.error(f"Error processing a match: {e}")
                continue
        
        return partidos
    
    def parse(self, raw_data):
        return raw_data

    def _extract_percentages(self, partido_div):
        """Extrae los porcentajes visibles del HTML original de la quiniela."""
        container = partido_div.find(
            'div',
            class_='c-boleto-multiples__base__app_caja_base__porcentajes__container'
        )
        if not container:
            return {}

        blocks = container.find_all('app-boleto-multiples-porcentajes')
        parsed_blocks = [self._parse_percentage_block(block) for block in blocks]
        parsed_blocks = [block for block in parsed_blocks if block]

        labels = ['jugados', 'lae', 'probables', 'jugados_repetido']
        return {
            label: parsed_blocks[index]
            for index, label in enumerate(labels)
            if index < len(parsed_blocks)
        }

    def _parse_percentage_block(self, block):
        """Parsea un bloque 1/X/2 con valor y tendencia visual."""
        row = block.find('div', class_='c-boleto-multiples-porcentajes__row')
        if not row:
            return None

        signs = ['1', 'X', '2']
        values = {}
        cells = row.find_all('div', class_='c-boleto-multiples-porcentajes__row__normal')
        for sign, cell in zip(signs, cells):
            spans = cell.find_all('span')
            value_text = spans[0].get_text(strip=True) if spans else '-'
            trend = 'flat'
            icon = cell.find('span', class_='fa-long-arrow-up')
            if icon:
                trend = 'up'
            elif cell.find('span', class_='fa-long-arrow-down'):
                trend = 'down'

            values[sign] = {
                'value': value_text,
                'trend': trend,
            }

        return values

    def run(self):
        """Executes the scraper complete."""
        self.logger.info(f"Iniciando {self.name}")
        raw = self.fetch()
        parsed = self.parse(raw)
        self.logger.info(f"Completado: {len(parsed)} items")
        return parsed
