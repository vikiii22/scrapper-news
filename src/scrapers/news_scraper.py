from typing import List, Dict, Any
from bs4 import BeautifulSoup
import requests
import logging
from src.scrapers.base import BaseScraper
from src.utils.http_client import http_client

class NewsScraper(BaseScraper):
    """
    Scraper for fetching news from sports sites (Marca, AS, etc.)
    and extracting relevant information (player status, logistic issues).
    """

    # Simple list of sources.
    SOURCES = [
        "https://www.marca.com/futbol/primera-division.html",
        # "https://www.as.com/futbol/primera"
    ]
    
    LOGISTIC_TERMS = [
        "neutral", "estadio neutral", "puerta cerrada", "sin público",
        "clausura", "cancha prestada", "otro estadio", "obras", "remodelación",
        "butarque" # Explicit mention in GEMINI.md
    ]

    def __init__(self):
        super().__init__("NewsScraper")
        # self.logger is initialized in BaseScraper but we can update it
        self.logger = logging.getLogger("scraper.news")

    def fetch_article(self, url: str) -> str:

        """Fetches the content of a news article or page."""
        try:
            response = http_client.get(url, timeout=10)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            self.logger.error(f"Error fetching {url}: {e}")
            return ""

    def parse_logistic_issues(self, text: str) -> List[str]:
        """Detects logistic anomalies in the text."""
        found_issues = []
        text_lower = text.lower()
        
        for term in self.LOGISTIC_TERMS:
            if term in text_lower:
                found_issues.append(term)
                
        return list(set(found_issues))

    def parse_player_status(self, text: str, player_names: List[str]) -> List[Dict[str, str]]:
        """
        Scans text for player names associated with 'baja', 'lesión', 'duda'.
        This is a very simple keyword distance heuristic.
        """
        status_keywords = ["lesion", "baja", "duda", "molestia", "sancion", "sancionado"]
        text_lower = text.lower()
        
        player_issues = []
        
        for player in player_names:
            p_name = player.lower()
            if p_name in text_lower:
                # Check for keywords in a window around the name
                idx = text_lower.find(p_name)
                start = max(0, idx - 50)
                end = min(len(text_lower), idx + len(p_name) + 50)
                context = text_lower[start:end]
                
                for kw in status_keywords:
                    if kw in context:
                        player_issues.append({
                            "player": player,
                            "status": kw,
                            "context": context
                        })
                        break # One status is enough
                        
        return player_issues

    def fetch(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Fetches news from all configured sources.
        """
        raw_htmls = []
        for url in self.SOURCES:
            self.logger.info(f"Fetching {url}...")
            html = self.fetch_article(url)
            if html:
                raw_htmls.append({"url": url, "content": html})
        return raw_htmls

    def parse(self, raw_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Parses the list of HTML contents.
        """
        all_news_data = {
            "logistic_issues": [],
            "player_issues": [],
            "sources_scraped": []
        }
        
        # Determine player names context (could be passed in run or hardcoded/global)
        # For strict compliance, we should parse just the text first.
        # But here I'll extract text and run the logic.
        
        for item in raw_data:
            url = item["url"]
            html = item["content"]
            
            soup = BeautifulSoup(html, 'html.parser')
            paragraphs = soup.find_all('p')
            text_content = " ".join([p.get_text() for p in paragraphs])
            
            # 1. Logistic Issues
            issues = self.parse_logistic_issues(text_content)
            if issues:
                all_news_data["logistic_issues"].extend([
                    {"source": url, "issue": issue} for issue in issues
                ])
                
            all_news_data["sources_scraped"].append(url)
            
            # Player issues would require player names context which BaseScraper.parse 
            # signature makes hard to pass dynamically unless self state.
            
        return all_news_data

    def run(self, player_names: List[str] = []) -> Dict[str, Any]:
        """
        Runs the scraper against configured sources.
        player_names is optional for specific player status check.
        """
        self.logger.info("Starting News Scraper...")
        
        raw_data = self.fetch()
        parsed_data = self.parse(raw_data)
        
        # Enhanced parsing if player names are provided (runtime context)
        if player_names:
            for item in raw_data:
                soup = BeautifulSoup(item["content"], 'html.parser')
                text_content = soup.get_text()
                
                p_issues = self.parse_player_status(text_content, player_names)
                if p_issues:
                     parsed_data["player_issues"].extend([
                         {**issue, "source": item["url"]} for issue in p_issues
                     ])
        
        self.logger.info("News Scraper finished.")
        return parsed_data

