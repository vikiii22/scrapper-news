import requests
from bs4 import BeautifulSoup
import json

class SportsNewsScraper:
    def __init__(self, url):
        self.url = url

    def fetch_news(self):
        response = requests.get(self.url)
        if response.status_code == 200:
            response.encoding = 'utf-8'
            return response.text
        else:
            return None

    def parse_news(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        headlines = soup.find_all('h2')
        data = []
        for headline in headlines:
            img = headline.find_previous('img')
            url = headline.find_previous('a')['href']
            if img:
                data.append({
                    'title': headline.text.strip(),
                    'image': img['src'],
                    'url': url
                })
        return data

    def save_news(self, headlines, file_path):
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(headlines, file, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    periodicos = ['https://www.marca.com/', 'https://www.sport.es/es/', 'https://www.as.com/']
    for periodico in periodicos:
        url = periodico
        scraper = SportsNewsScraper(url)
        html_content = scraper.fetch_news()
        if html_content:
            headlines = scraper.parse_news(html_content)
            file_path = f"../data/sports_news_{periodico.split('.')[1]}.json"
            scraper.save_news(headlines, file_path)