# Sports News Scraper

Este proyecto es un scraper de resultados deportivos escrito en Python.

## Estructura del Proyecto

- `scraper/`: Contiene el código principal del scraper.
- `tests/`: Contiene las pruebas unitarias.
- `data/`: Directorio para almacenar los datos extraídos.
- `requirements.txt`: Lista de dependencias del proyecto.
- `README.md`: Documentación del proyecto.

## Instalación

1. Clona el repositorio.
2. Instala las dependencias con `pip install -r requirements.txt`.

## Uso

Ejecuta el script principal:

```sh
python scraper/scraper.py
```

## Scrapers Disponibles

El proyecto incluye múltiples scrapers para diferentes fuentes de datos deportivos:

1. **SoccerData Scraper** - Extrae datos de resultados de fútbol desde SoccerData
2. **Segunda División Scraper** - Obtiene información de la Segunda División española
3. **Fútbol Español Scraper** - Recopila datos de la Liga Española y otras competiciones nacionales
4. **Quiniela Analysis** - Analiza y procesa datos de quinielas deportivas

Para ejecutar un scraper específico, consulta la documentación en la carpeta `scraper/`.