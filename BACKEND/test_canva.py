import requests
from bs4 import BeautifulSoup
import json

def scrape_canva_templates():
    url = "https://www.canva.com/resumes/templates/free/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    }
    
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    templates = []
    
    for item in soup.select('[data-testid="template-card"]'):
        template = {
            'title': item.select_one('h3').text.strip(),
            'thumbnail': item.select_one('img')['src'],
            'url': 'https://www.canva.com' + item.select_one('a')['href']
        }
        templates.append(template)
    
    with open('canva_templates.json', 'w') as f:
        json.dump(templates, f, indent=2)
    
    return templates

scrape_canva_templates()