import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from playwright.sync_api import sync_playwright

from src.scrapers.base import BaseScraper

class SofascoreScraper(BaseScraper):
    """
    Scraper for fetching football data from the Sofascore API using Playwright.
    """
    BASE_URL = "https://api.sofascore.com/api/v1"

    def __init__(self):
        super().__init__("Sofascore")
        # Session and headers are no longer needed here as Playwright manages them.

    def _fetch_api_data(self, endpoint: str) -> Dict[str, Any]:
        """
        Fetches data from a specific Sofascore API endpoint using Playwright.
        """
        url = f"{self.BASE_URL}/{endpoint}"
        self.logger.info(f"Fetching data from: {url} using Playwright")
        
        try:
            with sync_playwright() as p:
                browser = None
                
                # Argumentos para evitar detección de bot
                launch_args = [
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-infobars",
                    "--window-position=0,0",
                    "--ignore-certificate-errors",
                    "--mute-audio"
                ]

                try:
                    # Intento 1: Chromium bundled
                    browser = p.chromium.launch(headless=True, args=launch_args)
                except Exception as e1:
                    # Intento 2: Usar Chrome instalado en el sistema
                    self.logger.warning(f"Error launching bundled Chromium: {e1}. Trying system Chrome...")
                    try:
                        browser = p.chromium.launch(headless=True, channel="chrome", args=launch_args)
                    except Exception as e2:
                         # Intento 3: Usar Edge instalado en el sistema
                        self.logger.warning(f"Error launching system Chrome: {e2}. Trying Edge...")
                        browser = p.chromium.launch(headless=True, channel="msedge", args=launch_args)
                
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080},
                    locale="es-ES"
                )
                
                # Inyectar script para ocultar webdriver
                context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                """)

                page = context.new_page()

                # Go to the main site first to establish session/cookies with sufficient wait
                self.logger.info("Navigating to sofascore.com to initialize session.")
                try:
                    page.goto("https://www.sofascore.com", wait_until="domcontentloaded", timeout=60000)
                    # Small random wait to look like a human reading
                    # Using page.wait_for_timeout instead of time.sleep
                    page.wait_for_timeout(5000) 
                except Exception as e:
                     self.logger.warning(f"Error loading main page: {e}")

                # Now, fetch the API data using page.evaluate (fetch inside the browser context)
                self.logger.info(f"Fetching {url} inside browser context...")
                
                # Removed explicit User-Agent in fetch headers as navigator.userAgent provides it naturally
                # Added 'Sec-Fetch-Site': 'same-site' and others to mimic browser better
                js_fetch = f"""
                    async () => {{
                        try {{
                            const response = await fetch('{url}', {{
                                method: 'GET',
                                headers: {{
                                    'Accept': 'application/json, text/plain, */*',
                                    'Referer': 'https://www.sofascore.com/',
                                    'Origin': 'https://www.sofascore.com',
                                    'Sec-Fetch-Dest': 'empty',
                                    'Sec-Fetch-Mode': 'cors',
                                    'Sec-Fetch-Site': 'same-site',
                                }}
                            }});
                            if (response.status === 200) {{
                                return await response.json();
                            }}
                            return {{ 'status': response.status }};
                        }} catch (e) {{
                            return {{ 'status': 'error', 'message': e.toString() }};
                        }}
                    }}
                """
                
                data = page.evaluate(js_fetch)
                
                # The JS code returns the JSON object if status is 200.
                # If status is NOT 200, it returns { 'status': http_code }.
                # So we simply check if the returned data has our error structure.
                
                if isinstance(data, dict) and 'status' in data:
                    # Check if it matches our error signature (small dict with status code or error message)
                    if len(data) <= 2 and isinstance(data['status'], (int, str)) and 'error' in str(data.get('status', '')).lower() or isinstance(data['status'], int):
                        # Verify it's not a valid response that happens to have "status" key
                         # Our error object is { 'status': 403 } or { 'status': 'error', 'message': ... }
                         # Real data usually has many keys. 
                         # Let's assume if it is exactly {status: code} it is our error.
                         
                         # However, to be safe, let's rely on the fact that if it was 200, it is the API response.
                         # If it was 403, it's our error object.
                         # But we can't tell 200 from 403 just by "status" key existence if the API also returns "status".
                         
                         # Wait, my JS logic is:
                         # if (response.status === 200) return json();
                         # else return { 'status': response.status };
                         
                         # So if I receive { "status": 403 }, it is an error.
                         # If I receive { "status": "active", ... }, it is a success (because JS only returned it if 200).
                         
                         val = data['status']
                         if isinstance(val, int) and val != 200:
                             self.logger.error(f"Failed to fetch {url}. Status: {val}")
                             return {}
                         if isinstance(val, str) and val == 'error': # catastrophic fetch error
                             self.logger.error(f"Failed to fetch {url}. Setup error: {data.get('message')}")
                             return {}
                
                self.logger.info(f"Successfully fetched data for endpoint: {endpoint}")
                return data

        except Exception as e:
            self.logger.error(f"Error fetching {url} with Playwright: {e}")
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
        Fetches and processes all played matches for a season using team-events/total.
        """
        endpoint = f"unique-tournament/{tournament_id}/season/{season_id}/team-events/total"
        raw_data = self._fetch_api_data(endpoint)
        
        # Extract events from the nested structure specific to team-events endpoint
        events = []
        if 'tournamentTeamEvents' in raw_data:
            for t_data in raw_data['tournamentTeamEvents'].values():
                for s_data in t_data.values():
                    events.extend(s_data)
        
        # We construct a fake data dict to reuse _parse_matches logic
        # Note: _parse_matches splits into played/pending. Here we want played.
        processed = self._parse_matches({'events': events})
        return processed.get('played', [])

    def get_next_matches(self, tournament_id: int, season_id: int) -> List[Dict[str, Any]]:
        """
        Fetches and processes upcoming matches.
        """
        endpoint = f"unique-tournament/{tournament_id}/season/{season_id}/events/next/0"
        raw_data = self._fetch_api_data(endpoint)
        parsed = self._parse_matches(raw_data)
        return parsed.get('pending', [])

    def get_match_lineups(self, match_id: int) -> Dict[str, Any]:
        """
        Fetches lineups and missing players for a specific match.
        """
        endpoint = f"event/{match_id}/lineups"
        raw_data = self._fetch_api_data(endpoint)
        return self._parse_lineups(raw_data)

    def get_match_statistics(self, match_id: int) -> Dict[str, Any]:
        """
        Fetches match statistics (xG, SOG, etc).
        """
        endpoint = f"event/{match_id}/statistics"
        raw_data = self._fetch_api_data(endpoint)
        return self._parse_statistics(raw_data)

    def _parse_statistics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parses statistics to extract xG, SOG."""
        if not data or 'statistics' not in data:
            return {}
            
        stats_list = data.get('statistics', [])
        total_stats = None
        
        # Searching for 'ALL' or 'Total' period
        for stat_group in stats_list:
             if stat_group.get('period') == 'ALL':
                 total_stats = stat_group
                 break
        
        if not total_stats:
            return {}
            
        parsed = {
            'home_xg': 0.0,
            'away_xg': 0.0,
            'home_sog': 0,
            'away_sog': 0,
            'home_possession': 0,
            'away_possession': 0
        }
        
        for group in total_stats.get('groups', []):
            for item in group.get('statisticsItems', []):
                name = item.get('name')
                home_val = item.get('home')
                away_val = item.get('away')
                
                try:
                    if name == 'Expected goals':
                        parsed['home_xg'] = float(home_val) if home_val else 0.0
                        parsed['away_xg'] = float(away_val) if away_val else 0.0
                    elif name == 'Shots on goal':
                        parsed['home_sog'] = int(home_val) if home_val else 0
                        parsed['away_sog'] = int(away_val) if away_val else 0
                    elif name == 'Ball possession':
                        parsed['home_possession'] = int(str(home_val).replace('%','')) if home_val else 50
                        parsed['away_possession'] = int(str(away_val).replace('%','')) if away_val else 50
                except (ValueError, AttributeError):
                    continue

        return parsed

    def _parse_lineups(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parses lineups to extract ratings and confirmed players."""
        if not data:
            return {}
            
        home = data.get('home', {})
        away = data.get('away', {})
        
        parsed = {
            'home_confirmed': home.get('confirmedLineups', False),
            'away_confirmed': away.get('confirmedLineups', False),
            'home_players': [],
            'away_players': []
        }
        
        def extract_players(team_data, target_list):
            for p in team_data.get('players', []):
                rating = 0.0
                stats = p.get('statistics', {})
                if stats:
                    rating = float(stats.get('rating', 0.0))
                    
                target_list.append({
                    'name': p.get('player', {}).get('name'),
                    'id': p.get('player', {}).get('id'),
                    'rating': rating,
                    'position': p.get('position', 'sub'),
                    'substitute': p.get('substitute', False)
                })
        
        extract_players(home, parsed['home_players'])
        extract_players(away, parsed['away_players'])
            
        return parsed




    def _parse_standings(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Processes the raw standings data."""
        if not data or 'standings' not in data:
            self.logger.warning("No standings data found in the response.")
            return []

        standings_list = []
        # The standings are usually in a list, we take the first one
        if not data['standings']:
             return []
             
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
        events = data.get('events', [])
        if not events:
             return {'played': [], 'pending': []}

        played_matches = []
        pending_matches = []
        seen_ids = set()
        
        for event in events:
            event_id = event.get('id')
            if event_id in seen_ids:
                continue
            seen_ids.add(event_id)

            home_team = event.get('homeTeam', {})
            away_team = event.get('awayTeam', {})
            status = event.get('status', {})
            
            match_info = {
                'id': event_id,
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
        
        # Sort by date
        played_matches.sort(key=lambda x: x['date'])
        pending_matches.sort(key=lambda x: x['date'])

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
        return raw_data if isinstance(raw_data, list) else [raw_data] 

    def run(self, **kwargs) -> List[Dict]:
        """Executes the scraper complete."""
        self.logger.info(f"Running {self.name} scraper...")
        data = self.fetch(**kwargs)
        # In this structure, fetch returns a dict with processed data
        # parse is technically redundant but we keep base structure
        # ensuring return is consistent
        self.logger.info(f"Finished running {self.name} scraper.")
        return [data]
