import requests
from bs4 import BeautifulSoup
import json

class AnalysisScraper:
    def __init__(self, urls):
        self.urls = urls

    def fetch_analysis(self, url):
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

    def parse_analysis(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        stat_rows = soup.find_all('div', class_='panel-body')

        # Lista para almacenar los datos
        elo_data = []

        # Iterar sobre cada 'panel-body'
        for row in stat_rows:
            # Diccionario para almacenar los datos de cada 'panel-body'
            row_data = {}
            
            # Buscar el ELO de los equipos
            team1_elo = row.find('td', class_='team1-c')
            team2_elo = row.find('td', class_='team2-c')
            
            if team1_elo and team2_elo:
                row_data['team1_elo'] = team1_elo.text.strip()
                row_data['team2_elo'] = team2_elo.text.strip()
            
            # Buscar los nombres de los equipos en el alt de las imágenes
            images = row.find_all('img')

            # Asegurarse de que hay al menos dos imágenes
            if len(images) >= 2:
                team1_img = images[0]
                team2_img = images[1]
                
                if team1_img and team2_img:
                    row_data['team1_name'] = team1_img['alt'].strip()
                    row_data['team2_name'] = team2_img['alt'].strip()
            
            # Buscar las probabilidades de victoria
            elo_bar = row.find('div', class_='elo-bar')
            if elo_bar:
                team1_bar = elo_bar.find('div', class_='team1-bar')
                draw_bar = elo_bar.find('div', class_='draw-bar')
                team2_bar = elo_bar.find('div', class_='team2-bar')
                
                if team1_bar and draw_bar and team2_bar:
                    row_data['team1_prob'] = team1_bar['style'].split(':')[1].strip()
                    row_data['draw_prob'] = draw_bar['style'].split(':')[1].strip()
                    row_data['team2_prob'] = team2_bar['style'].split(':')[1].strip()
            
            # Añadir los datos de la fila a la lista
            if row_data:
                elo_data.append(row_data)

        # Posibles resultados

        probabli_results = soup.find('div', class_='panel possible-results')

        panel = probabli_results.find_all('div', class_='panel-body')

        for result in panel:
            result_data = {
                'exact_results': [],
                'goal_differences': [],
                'probabilities': [],
                'expected_goals': []
            }
            
            lines = result.text.split('\n')
            
            # Filtrar y limpiar las líneas
            lines = [line.strip() for line in lines if line.strip()]
            
            category = None
            for line in lines:
                if 'Probabilidad de cada resultado exacto' in line:
                    category = 'exact_results'
                elif 'Probabilidad de cada diferencia de goles' in line:
                    category = 'goal_differences'
                elif 'Probabilidad gana' in line:
                    category = 'probabilities'
                elif 'Goles esperados' in line:
                    category = 'expected_goals'
                elif category:
                    result_data[category].append(line)
            
            # Añadir el diccionario resultante a la lista elo_data
            if result_data:
                elo_data.append(result_data)
            
        # Imprimir los datos recogidos
        return elo_data

    def scrape(self):
        all_analysis = []
        
        for url in self.urls:
            html_content = self.fetch_analysis(url)
            if html_content:
                analysis_data = self.parse_analysis(html_content)
                all_analysis.append(analysis_data)
        
        return all_analysis

    def save_results(self, results, file_path):
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(results, file, ensure_ascii=False, indent=4)

if __name__ == "__main__":

    # Cargar los resultados desde el archivo JSON existente
    with open("../data/big-data.json", 'r', encoding='utf-8') as file:
        matches = json.load(file)

    # Extraer todas las URLs de análisis
    analysis_urls = [match['analysis_url'] for match in matches]

    # Crear la instancia del scraper y ejecutar la recolección de datos
    scraper = AnalysisScraper(analysis_urls)
    analysis_results = scraper.scrape()

    # Guardar los resultados en un archivo JSON
    scraper.save_results(analysis_results, "../data/analysis_results.json")
    print("Resultados de análisis guardados.")
