import requests
from bs4 import BeautifulSoup
import json

class TeamIdScraper:
    def __init__(self, urls):
        self.urls = urls

    def fetch_classification(self, url):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) ' 
                          'AppleWebKit/537.36 (KHTML, like Gecko) ' 
                          'Chrome/58.0.3029.110 Safari/537.3'
        }
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()  # Lanza una excepción si el código no es 200
            response.encoding = 'utf-8'
            return response.text
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err}")
        except Exception as err:
            print(f"Other error occurred: {err}")
        return None

    def parse_classification(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        teams_data = {}

        # Encuentra la tabla de clasificación
        table = soup.find('table', class_='table')
        if not table:
            print("No se encontró la tabla de clasificación.")
            return teams_data

        rows = table.find_all('tr')
        for row in rows[1:]:  # Saltar la cabecera
            cols = row.find_all('td')
            if len(cols) < 2:  # Asegurarse de que hay suficientes columnas
                continue
            
            # Extraer el nombre del equipo y el ID
            team_name_tag = cols[2].find('a')  # Columna con el nombre del equipo
            if team_name_tag:
                team_name = team_name_tag.text.strip()
                team_id = team_name_tag['href'].split('/')[-1]  # Obtener el ID desde la URL
                teams_data[team_name] = team_id

        return teams_data

    def scrape(self):
        all_teams = {}
        for url in self.urls:
            html_content = self.fetch_classification(url)
            if html_content:
                teams = self.parse_classification(html_content)
                all_teams.update(teams)
        
        return all_teams

if __name__ == "__main__":
    urls = [
        "https://es.besoccer.com/competicion/clasificacion/primera",
        "https://es.besoccer.com/competicion/clasificacion/segunda"
    ]
    
    scraper = TeamIdScraper(urls)
    team_ids = scraper.scrape()

    # Guardar los IDs en un archivo JSON
    with open('team_ids.json', 'w', encoding='utf-8') as f:
        json.dump(team_ids, f, ensure_ascii=False, indent=4)

    print("IDs de equipos guardados en 'team_ids.json'.")
