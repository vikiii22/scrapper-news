"""Cliente HTTP con reintentos y caché."""
import requests
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def get_http_client() -> requests.Session:
    """Configura y devuelve una sesión de requests con reintentos."""
    session = requests.Session()
    
    # Headers básicos para simular un navegador real
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Referer": "https://www.google.com/"
    })

    retries = Retry(
        total=5,
        backoff_factor=2,  # Aumentar backoff para ser más gentil
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

http_client = get_http_client()
