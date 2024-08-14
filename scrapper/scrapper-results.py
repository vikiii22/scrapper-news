import requests
from bs4 import BeautifulSoup
import json

class ResultsSportsNewScrapper:
    def __init__(self, url):
        self.url = url

    def fetch_results(self):
        response = requests.get(self.url)
        if response.status_code == 200:
            response.encoding = 'utf-8'
            return response.text
        else:
            return None

    def parse_results(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        results = soup.find_all('div', class_='panel-body p0 match-list-new panel view-more')
        data = []
        for result in results:
            league_name = result.find_previous('span', class_='va-m').text.strip()
            league_image = result.find_previous('img', class_='comp-img')['src']
            matches = result.find_all('a', class_='match-link')
            for match in matches:
                if match.find('div', class_='team-name ta-r team_left') is None:
                    continue
                if match.find('div', class_='team-name ta-l team_right') is None:
                    continue
                if match.find_all('img', class_='pv3 va-m team-shield') is None:
                    continue
                if match.find('p', class_='match_hour time') is None and match.find('span', class_='r1') is None:
                    continue

                team_a_name = match.find('div', class_='team-name ta-r team_left').text.strip()
                team_a_image = match.find_all('img', class_='pv3 va-m team-shield')[0]['src']
                team_b_name = match.find('div', class_='team-name ta-l team_right').text.strip()
                team_b_image = match.find_all('img', class_='pv3 va-m team-shield')[1]['src']
                
                # Extraer la hora del partido y el resultado
                match_time = match.find('p', class_='match_hour time')
                if match_time:
                    match_time = match_time.text.strip()
                    score_a = None
                    score_b = None
                else:
                    match_time = "Finalizado"
                    score_a = match.find('span', class_='r1').text.strip()
                    score_b = match.find('span', class_='r2').text.strip()

                data.append({
                    'league_name': league_name,
                    'league_image': league_image,
                    'team_a_name': team_a_name,
                    'team_a_image': team_a_image,
                    'team_b_name': team_b_name,
                    'team_b_image': team_b_image,
                    'match_time': match_time,
                    'score_a': score_a,
                    'score_b': score_b
                })
        return data

    def save_results(self, results, file_path):
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(results, file, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    periodicos = ['https://es.besoccer.com/']
    for periodico in periodicos:
        url = periodico
        scraper = ResultsSportsNewScrapper(url)
        html_content = scraper.fetch_results()
        if html_content:
            results = scraper.parse_results(html_content)
            file_path = f"../data/sports_results_{periodico.split('.')[1]}.json"
            scraper.save_results(results, file_path)