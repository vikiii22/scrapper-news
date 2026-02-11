import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.scrapers.base import BaseScraper
from src.utils.http_client import http_client

class SofascoreScraper(BaseScraper):
    """
    Scraper for fetching football data from the Sofascore API.
    """
    BASE_URL = "https://api.sofascore.com/api/v1"

    def __init__(self):
        super().__init__("Sofascore")
        self.client = http_client
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def _fetch_api_data(self, endpoint: str) -> Dict[str, Any]:
        """
        Fetches data from a specific Sofascore API endpoint.
        """
        url = f"{self.BASE_URL}/{endpoint}"
        self.logger.info(f"Fetching data from: {url}")
        try:
            response = self.client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"Error fetching {url}: {e}")
            return {}

    def get_standings(self, tournament_id: int, season_id: int) -> List[Dict[str, Any]]:
        """
        Fetches and processes the league standings.
        """
        endpoint = f"unique-tournament/{tournament_id}/season/{season_id}/standings/total"
        raw_data = self._fetch_api_data(endpoint)
        return self._parse_standings(raw_data)

    def get_all_matches(self, tournament_id: int, season_id: int) -> List[Dict[str, Any]]:
        """
        Fetches and processes all played matches for a season.
        """
        # Sofascore API for all events in a season seems to be structured this way
        endpoint = f"unique-tournament/{tournament_id}/season/{season_id}/events/last/0"
        raw_data = self._fetch_api_data(endpoint)
        parsed = self._parse_matches(raw_data)
        return parsed.get('played', [])

    def get_next_matches(self, tournament_id: int, season_id: int) -> List[Dict[str, Any]]:
        """
        Fetches and processes upcoming matches.
        """
        endpoint = f"unique-tournament/{tournament_id}/season/{season_id}/events/next/0"
        raw_data = self._fetch_api_data(endpoint)
        parsed = self._parse_matches(raw_data)
        return parsed.get('pending', [])

    def _parse_standings(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Processes the raw standings data."""
        if not data or 'standings' not in data:
            self.logger.warning("No standings data found in the response.")
            return []

        standings_list = []
        # The standings are usually in a list, we take the first one
        rows = data['standings'][0].get('rows', [])

        for row in rows:
            team = row.get('team', {})
            wins = row.get('wins', 0)
            draws = row.get('draws', 0)
            losses = row.get('losses', 0)
            matches_played = wins + draws + losses
            
            team_data = {
                'position': row.get('position', 0),
                'team_name': team.get('name', 'Unknown'),
                'team_id': team.get('id', 0),
                'points': row.get('points', 0),
                'matches_played': matches_played,
                'wins': wins,
                'draws': draws,
                'losses': losses,
                'goals_for': row.get('scoresFor', 0),
                'goals_against': row.get('scoresAgainst', 0),
                'goal_diff': row.get('scoresFor', 0) - row.get('scoresAgainst', 0)
            }
            standings_list.append(team_data)

        return standings_list

    def _parse_matches(self, data: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """Processes raw match data."""
        if not data or 'events' not in data:
            return {'played': [], 'pending': []}

        played_matches = []
        pending_matches = []
        
        for event in data['events']:
            home_team = event.get('homeTeam', {})
            away_team = event.get('awayTeam', {})
            status = event.get('status', {})
            
            match_info = {
                'id': event.get('id'),
                'round': event.get('roundInfo', {}).get('round', 0),
                'date': datetime.fromtimestamp(event.get('startTimestamp', 0)).strftime('%Y-%m-%d %H:%M:%S'),
                'home_team_name': home_team.get('name', 'Unknown'),
                'home_team_id': home_team.get('id', 0),
                'away_team_name': away_team.get('name', 'Unknown'),
                'away_team_id': away_team.get('id', 0),
                'status': status.get('description', 'unknown')
            }

            if status.get('type') == 'finished':
                home_score = event.get('homeScore', {}).get('current', 0)
                away_score = event.get('awayScore', {}).get('current', 0)
                match_info['home_score'] = home_score
                match_info['away_score'] = away_score
                match_info['result'] = '1' if home_score > away_score else ('2' if away_score > home_score else 'X')
                played_matches.append(match_info)
            else:
                pending_matches.append(match_info)
        
        return {'played': played_matches, 'pending': pending_matches}

    def fetch(self, **kwargs) -> Dict[str, Any]:
        """
        Main fetch method for the scraper.
        Fetches standings, all matches, and next matches.
        """
        tournament_id = kwargs.get("tournament_id")
        season_id = kwargs.get("season_id")

        if not tournament_id or not season_id:
            raise ValueError("tournament_id and season_id must be provided.")

        self.logger.info(f"Fetching all data for tournament {tournament_id}, season {season_id}")
        
        standings = self.get_standings(tournament_id, season_id)
        all_matches = self.get_all_matches(tournament_id, season_id)
        next_matches = self.get_next_matches(tournament_id, season_id)

        return {
            "standings": standings,
            "all_matches": all_matches,
            "next_matches": next_matches
        }

    def parse(self, raw_data: Any) -> List[Dict]:
        """
        The main parsing is done within the specific get methods.
        This method just returns the already processed data.
        """
        return [raw_data]

    def run(self, **kwargs) -> List[Dict]:
        """Executes the scraper complete."""
        self.logger.info(f"Running {self.name} scraper...")
        data = self.fetch(**kwargs)
        parsed_data = self.parse(data)
        self.logger.info(f"Finished running {self.name} scraper.")
        return parsed_data
