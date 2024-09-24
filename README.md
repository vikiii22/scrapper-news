# Sports News Scraper

Este proyecto es un scraper de noticias deportivas escrito en Python.

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


## El primer script a ejecutar será scrapper-data-besoccer.py para crear el archivo big-data.json
## El segundo será scrapper-analysis.py y posteriormente ese json que nos devuelva se lo mandamos a analizar al chat gpt.
## En caso de querer actualizar las competiciones deberemos ejecutar teams-scrapper.py