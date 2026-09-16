"""
Adaptador Selenium OPCIONAL.

Solo se usa si el usuario lo pide explícitamente (`use_selenium=True`)
y tiene selenium + chromedriver instalados. El resto del sistema
funciona SIN Selenium (requests + BeautifulSoup).

Ejemplo de uso manual:
    pip install selenium
    # + tener chromedriver en el PATH (o usar webdriver-manager)
"""

from __future__ import annotations

from typing import Optional


def is_available() -> bool:
    try:
        import selenium  # noqa: F401
        return True
    except ImportError:
        return False


def fetch_sofascore_js(team_name: str, headless: bool = True) -> Optional[str]:
    """
    Esqueleto para scraping JS-heavy (SofaScore/Soccerway) con Selenium.
    Devuelve la forma "WDL..." o None. No rompe si selenium no está instalado.
    """
    if not is_available():
        return None
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        import time
        import urllib.parse

        opts = Options()
        if headless:
            opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-gpu")
        driver = webdriver.Chrome(options=opts)
        try:
            q = urllib.parse.quote_plus(f"sofascore {team_name}")
            driver.get(f"https://www.google.com/search?q={q}")
            time.sleep(2)
            return None  # punto de partida: el usuario puede extenderlo
        finally:
            driver.quit()
    except Exception:
        return None
