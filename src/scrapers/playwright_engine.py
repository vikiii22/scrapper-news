"""Motor de scraping basado en Playwright."""
import logging
from typing import Optional, Dict, Any
from playwright.sync_api import sync_playwright, Browser, Page

class PlaywrightEngine:
    """Motor de navegación web usando Playwright."""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.logger = logging.getLogger("scraper.playwright")
        self._playwright = None
        self._browser: Optional[Browser] = None
        
    def __enter__(self):
        self.start()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        
    def start(self):
        """Inicia la sesión de Playwright."""
        if not self._playwright:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=self.headless)
            self.logger.info("Playwright iniciado")
            
    def stop(self):
        """Detiene la sesión."""
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()
        self.logger.info("Playwright detenido")
            
    def get_page_content(self, url: str, wait_selector: Optional[str] = None) -> str:
        """
        Obtiene el contenido HTML de una página.
        
        Args:
            url: URL a visitar
            wait_selector: Selector CSS a esperar antes de devolver contenido
        """
        if not self._browser:
            self.start()
            
        page = self._browser.new_page()
        try:
            self.logger.info(f"Navegando a {url}")
            page.goto(url)
            
            if wait_selector:
                page.wait_for_selector(wait_selector)
                
            return page.content()
        except Exception as e:
            self.logger.error(f"Error navegando a {url}: {e}")
            raise
        finally:
            page.close()
