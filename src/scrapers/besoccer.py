import datetime
import json
import unidecode
from bs4 import BeautifulSoup
from typing import Any, Dict, List, Optional

from src.scrapers.base import BaseScraper
from src.utils.http_client import http_client

class BeSoccerScraper(BaseScraper):
    """
    Scraper for BeSoccer to get match results and upcoming matches.
    """
    BASE_URL = "https://es.besoccer.com/livescore/"

    def __init__(self, allowed_leagues: List[str]):
        """
        Initializes the BeSoccerScraper.

        Args:
            allowed_leagues: A list of league names to scrape.
        """
        super().__init__("BeSoccer")
        self.allowed_leagues = allowed_leagues
        self.team_name_mappings = self._load_team_name_mappings()

    def _load_team_name_mappings(self) -> Dict[str, str]:
        """Loads team name mappings from a JSON file."""
        try:
            with open('src/config/team_ids.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.warning("team_ids.json not found. Team names will not be mapped.")
            return {}

    def fetch(self, date: datetime.date) -> Optional[str]:
        """
        Fetches the HTML content for a specific date from BeSoccer.

        Args:
            date: The date for which to fetch the match data.

        Returns:
            The HTML content of the page as a string, or None if an error occurs.
        """
        url = f"{self.BASE_URL}{date.strftime('%Y-%m-%d')}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Referer': 'https://es.besoccer.com/',
            'DNT': '1',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        }
        try:
            response = http_client.get(url, headers=headers)
            response.raise_for_status()
            return response.text
        except Exception as e:
            self.logger.error(f"Error fetching {url}: {e}")
            return None

    def parse(self, html_content: str, date: datetime.date) -> List[Dict[str, Any]]:
        """
        Parses the HTML content to extract match data.

        Args:
            html_content: The HTML content of the page.
            date: The date of the matches.

        Returns:
            A list of dictionaries, each containing data for a match.
        """
        if not html_content:
            return []

        soup = BeautifulSoup(html_content, 'html.parser')
        data = []
        results = soup.find_all('div', class_='panel-body p0 match-list-new panel view-more')

        for result in results:
            league_name_tag = result.find_previous('span', class_='va-m')
            if not league_name_tag or league_name_tag.text.strip() not in self.allowed_leagues:
                continue

            league_name = league_name_tag.text.strip()
            league_image_tag = result.find_previous('img', class_='comp-img')
            league_image = league_image_tag['src'] if league_image_tag else None

            matches = result.find_all('a', class_='match-link')
            for match in matches:
                match_data = self._parse_match(match, league_name, league_image, date)
                if match_data:
                    data.append(match_data)
        return data

    def _parse_match(self, match_tag: BeautifulSoup, league_name: str, league_image: Optional[str], date: datetime.date) -> Optional[Dict[str, Any]]:
        """Parses a single match from its HTML tag."""
        team_a_tag = match_tag.find('div', class_='team-name ta-r team_left') or match_tag.find('div', class_='team-name ta-r')
        team_b_tag = match_tag.find('div', class_='team-name ta-l team_right') or match_tag.find('div', class_='team-name ta-l')

        if not team_a_tag or not team_b_tag:
            return None

        team_a_name = team_a_tag.text.strip()
        team_b_name = team_b_tag.text.strip()

        team_images = match_tag.find_all('img', class_='pv3 va-m team-shield')
        if len(team_images) < 2:
            return None

        team_a_image = team_images[0]['src']
        team_b_image = team_images[1]['src']

        match_time_tag = match_tag.find('p', class_='match_hour time')
        if match_time_tag:
            match_time = match_time_tag.text.strip()
            score_a, score_b = None, None
        else:
            match_time = "Finalizado"
            score_a = (match_tag.find('span', class_='r1') or {}).text.strip() or "N/A"
            score_b = (match_tag.find('span', class_='r2') or {}).text.strip() or "N/A"

        match_id = match_tag['href'].split('/')[-1]

        team_a_name_clean = self._clean_team_name(team_a_name)
        team_b_name_clean = self._clean_team_name(team_b_name)

        analysis_url = self._build_url("analisis", team_a_name_clean, team_b_name_clean, match_id, league_name)
        betting_url = self._build_url("apuestas-futbol", team_a_name_clean, team_b_name_clean, match_id, league_name)

        return {
            'league_name': league_name,
            'league_image': league_image,
            'team_a_name': team_a_name,
            'team_a_image': team_a_image,
            'team_b_name': team_b_name,
            'team_b_image': team_b_image,
            'match_time': match_time,
            'score_a': score_a,
            'score_b': score_b,
            'date': date.strftime('%Y-%m-%d'),
            'team_a_info': f"https://es.besoccer.com/equipo/plantilla/{team_a_name_clean}",
            'team_b_info': f"https://es.besoccer.com/equipo/plantilla/{team_b_name_clean}",
            'analysis_url': analysis_url,
            'url_apuestas': betting_url,
            'match_id': match_id
        }

    def _clean_team_name(self, name: str) -> str:
        """Cleans and maps a team name."""
        # Use mapping from team_ids.json first
        mapped_name = self.team_name_mappings.get(name, unidecode.unidecode(name))
        
        # Apply specific mappings
        specific_mappings = {
            'paises bajos': 'holanda',
            'espana': 'espanola'
        }
        return specific_mappings.get(mapped_name.lower(), mapped_name.lower())

    def _build_url(self, page: str, team_a: str, team_b: str, match_id: str, league: str) -> str:
        """Builds analysis or betting URLs for a match."""
        prefix = "seleccion-" if league == 'Liga de las Naciones de la UEFA' else ""
        return f"https://es.besoccer.com/partido/{prefix}{team_a}/{prefix}{team_b}/{match_id}/{page}"

    def run(self, start_date: datetime.date, num_days: int) -> List[Dict[str, Any]]:
        """
        Runs the scraper for a range of dates.

        Args:
            start_date: The starting date.
            num_days: The number of days to scrape from the start date.

        Returns:
            A list of all matches found in the date range.
        """
        all_matches = []
        for i in range(num_days):
            current_date = start_date + datetime.timedelta(days=i)
            self.logger.info(f"Scraping matches for {current_date.strftime('%Y-%m-%d')}")
            html = self.fetch(date=current_date)
            if html:
                matches = self.parse(html, date=current_date)
                all_matches.extend(matches)
        self.logger.info(f"Scraping finished. Found {len(all_matches)} matches in total.")
        return all_matches

if __name__ == '__main__':
    # Example of how to use the scraper
    allowed_leagues = [
        'Primera División',
        'Segunda División',
        'Liga de las Naciones de la UEFA'
    ]
    scraper = BeSoccerScraper(allowed_leagues=allowed_leagues)
    
    # Scrape today and the next 6 days
    today = datetime.date.today()
    results = scraper.run(start_date=today, num_days=7)

    if results:
        # Save to a file for inspection
        with open('data/besoccer_scraped_data.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
        print(f"Data saved to data/besoccer_scraped_data.json")
