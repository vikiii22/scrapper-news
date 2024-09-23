import requests
from bs4 import BeautifulSoup
import json
import datetime

class ResultsSportsNewScrapper:
    def __init__(self, url, allowed_leagues):
        self.url = url
        self.allowed_leagues = allowed_leagues

    def fetch_results(self):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) ' 
                          'AppleWebKit/537.36 (KHTML, like Gecko) ' 
                          'Chrome/58.0.3029.110 Safari/537.3'
        }
        try:
            response = requests.get(self.url, headers=headers)
            response.raise_for_status()  # Lanza una excepción si el código no es 200
            response.encoding = 'utf-8'
            return response.text
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err}")  # Manejar errores HTTP
        except Exception as err:
            print(f"Other error occurred: {err}")  # Otros errores
        return None

    def parse_results(self, html_content, date):
        soup = BeautifulSoup(html_content, 'html.parser')
        results = soup.find_all('div', class_='panel-body p0 match-list-new panel view-more')
        data = []
        for result in results:
            league_name = result.find_previous('span', class_='va-m').text.strip()
            if league_name not in self.allowed_leagues:
                continue  # Saltar ligas que no están en la lista permitida

            league_image_tag = result.find_previous('img', class_='comp-img')
            league_image = league_image_tag['src'] if league_image_tag else None

            matches = result.find_all('a', class_='match-link')
            for match in matches:
                # Bloque nombre equipo A
                team_a_tag = match.find('div', class_='team-name ta-r team_left') or \
                             match.find('div', class_='team-name ta-r team_left winner')
                team_a_name = team_a_tag.text.strip() if team_a_tag else None

                # Bloque nombre equipo B
                team_b_tag = match.find('div', class_='team-name ta-l team_right') or \
                             match.find('div', class_='team-name ta-l team_right winner')
                team_b_name = team_b_tag.text.strip() if team_b_tag else None

                # Verificar que ambos nombres de equipos existan
                if not team_a_name or not team_b_name:
                    print(f"Error: Nombres de equipos incompletos en la fecha {date}.")
                    continue

                # Bloque búsqueda de imagen de los equipos
                team_images = match.find_all('img', class_='pv3 va-m team-shield')
                if len(team_images) < 2:
                    print(f"Error: Imágenes de equipos incompletas en la fecha {date}.")
                    continue

                team_a_image = team_images[0]['src']
                team_b_image = team_images[1]['src']

                # Extraer la hora del partido y el resultado
                match_time_tag = match.find('p', class_='match_hour time')
                if match_time_tag:
                    match_time = match_time_tag.text.strip()
                    score_a = None
                    score_b = None
                else:
                    match_time = "Finalizado"
                    score_a_tag = match.find('span', class_='r1')
                    score_b_tag = match.find('span', class_='r2')
                    score_a = score_a_tag.text.strip() if score_a_tag else "N/A"
                    score_b = score_b_tag.text.strip() if score_b_tag else "N/A"

                # Extraer ID del partido para el análisis
                match_id = match['href'].split('/')[-1]  # Obtiene el ID del enlace

                # Construir la URL de análisis sin guiones ni la palabra 'real'
                team_a_name_clean = team_a_name.replace(" ", "").replace("Real", "")
                team_b_name_clean = team_b_name.replace(" ", "").replace("Real", "")
                analysis_url = f"https://es.besoccer.com/partido/{team_a_name_clean.lower()}/{team_b_name_clean.lower()}/{match_id}/analisis"

                data.append({
                    'league_name': league_name,
                    'league_image': league_image,
                    'team_a_name': team_a_name,
                    'team_a_image': team_a_image,
                    'team_b_name': team_b_name,
                    'team_b_image': team_b_image,
                    'match_time': match_time,
                    'score_a': score_a,
                    'score_b': score_b,
                    'date': date,
                    'analysis_url': analysis_url  # Agregar la URL de análisis
                })
        return data

    def save_results(self, results, file_path):
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(results, file, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    # Definir las ligas permitidas
    allowed_leagues = [
        'Primera División',
        'Segunda División',
        'Champions League',
        'Europa League'
    ]

    base_url = 'https://es.besoccer.com/livescore/'
    
    # Generar las fechas: hoy y los próximos 3 días
    today = datetime.datetime.now()
    future_days = [today + datetime.timedelta(days=i) for i in range(4)]  # 0 a 3 días futuros
    urls = [f'{base_url}{day.strftime("%Y-%m-%d")}' for day in future_days]

    file_path = "../data/big-data.json"
    all_results = []

    for url in urls:
        dateMatch = url.split("/")[-1]
        scraper = ResultsSportsNewScrapper(url, allowed_leagues)
        html_content = scraper.fetch_results()
        if html_content:
            results = scraper.parse_results(html_content, dateMatch)
            all_results.extend(results)
        else:
            print(f"No se pudieron obtener resultados para la fecha {dateMatch}.")

    # Guardar los resultados una vez que se hayan recolectado todos los partidos.
    if all_results:
        scraper.save_results(all_results, file_path)
        print(f"Resultados guardados en {file_path}")
    else:
        print("No se encontraron resultados para las ligas especificadas.")
