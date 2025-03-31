import pycurl
from io import BytesIO
from bs4 import BeautifulSoup
import json

class TeamsAnalysis:
    def __init__(self, urls):
        self.urls = urls

    def fetch_analysis(self, url):
        headers = [
            'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/58.0.3029.110 Safari/537.3'
        ]

        buffer = BytesIO()
        c = pycurl.Curl()
        c.setopt(c.URL, url)
        c.setopt(c.HTTPHEADER, headers)
        c.setopt(c.WRITEDATA, buffer)
        try:
            c.perform()
            status_code = c.getinfo(pycurl.RESPONSE_CODE)
            c.close()
            if status_code == 200:
                response_text = buffer.getvalue().decode('utf-8')
                return response_text
            else:
                print(url)
                print(f"HTTP error occurred: {status_code}")
        except pycurl.error as err:
            print(f"Other error occurred: {err}")
        return None
    
    def parse_analysis(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Buscar las filas de jugadores en la tabla
        player_rows = soup.find_all('tr', class_='row-body')
        players_data = []

        for row in player_rows:
            try:
                # Extraer datos del jugador con validaciones
                number = row.find('td', class_='number-box')
                number = number.text.strip() if number else 'N/A'

                name = row.find('td', class_='name')
                name = name.text.strip() if name else 'N/A'

                position = row.find('script', type='application/ld+json')
                position_data = json.loads(position.text) if position else {}
                job_title = position_data.get('jobTitle', 'N/A')

                nationality = row.find('td img')
                nationality = nationality.get('alt', 'N/A') if nationality else 'N/A'

                performance_data = row.find_all('td', {'data-content-tab': 'team_performance'})
                performance_values = [td.text.strip() for td in performance_data]

                # Asignar valores según el orden esperado
                matches = performance_values[0] if len(performance_values) > 0 else '0'
                total_matches = performance_values[1] if len(performance_values) > 0 else '0'
                goals = performance_values[2] if len(performance_values) > 1 else '0'
                assists = performance_values[3] if len(performance_values) > 2 else '0'
                cards = performance_values[4] if len(performance_values) > 3 else '0'

                elo_team = row.find('div', class_='elo label-text')
                elo_team = elo_team.text.strip() if elo_team else 'N/A'

                # Agregar los datos del jugador a la lista
                players_data.append({
                    'number': number,
                    'name': name,
                    'position': job_title,
                    'nationality': nationality,
                    'total_matches': total_matches,
                    'matches': matches,
                    'goals': goals,
                    'assists': assists,
                    'cards': cards
                })
            except Exception as e:
                print(f"Error parsing player data: {e}")
        
        return players_data
    
    def parse_players(self, url):
        featured_url = url.replace('/plantilla', '')
        html_content = self.fetch_analysis(featured_url)
        if html_content:
            soup = BeautifulSoup(html_content, 'html.parser')
            players_data = []
            featured_section = soup.find('div', class_='panel player-team-squad team-featured-players')
            players = featured_section.find_all('a', {'data-cy': 'featuredPlayer'})
            for player in players:
                try:
                    name = player.find('div', class_='person-name').text.strip()
                    number = player.find('span', class_='number').text.strip()
                    position = player.find('span', class_='bg-role').text.strip()
                    image = player.find('img', class_='player-circle-box')['src']
                    elo = player.find('div', class_='row jc-ce').find('div').text.strip()

                    players_data.append({
                        'name': name,
                        'number': number,
                        'position': position,
                        'image': image,
                        'elo': elo
                    })
                except Exception as e:
                    print(f"Error parsing featured player data: {e}")
            return players_data
        return []


    def parse(self):
        all_data = {}
        for url in self.urls:
            html_content = self.fetch_analysis(url)
            if html_content:
                # Extraer el nombre del equipo desde la URL o el contenido HTML
                soup = BeautifulSoup(html_content, 'html.parser')
                team_name = soup.find('title').text.strip() if soup.find('title') else url.split('/')[-1]
                
                # Parsear los datos de los jugadores
                players_data = self.parse_analysis(html_content)

                most_valuated_players = self.parse_players(url)
                
                # Guardar los datos bajo el nombre del equipo
                all_data[team_name] = {
                    'players_data': players_data,
                    'top_players': most_valuated_players
                }
        return all_data
    
    def save_results(self, results, file_path):
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(results, file, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    with open("../data/big-data.json", 'r', encoding='utf-8') as file:
        matches = json.load(file)

    teams_urls = [match['team_a_info'] for match in matches] + [match['team_b_info'] for match in matches]

    scraper = (TeamsAnalysis(teams_urls))
    analysis_results = scraper.parse()

    scraper.save_results(analysis_results, "../data/teams_analysis_results.json")
    print("Resultados de equipos guardados.")