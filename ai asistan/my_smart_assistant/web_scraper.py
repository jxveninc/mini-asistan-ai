# my_smart_assistant/web_scraper.py
# Bu dosya, Wikipedia API entegrasyonundan sonra aktif olarak kullanılmamaktadır.
# Ancak projeden kaldırılmamıştır.
import requests
from bs4 import BeautifulSoup

def fetch_and_clean_text(url):
    """URL'den metin çeker (şu anki projede Wikipedia API kullanıldığı için atıl durumdadır)."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
            'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7', 
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status() 
        soup = BeautifulSoup(response.content, 'html.parser')
        
        for script_or_style in soup(['script', 'style', 'header', 'footer', 'nav', 'noscript', 'img', 'form', 'button', 'input']):
            script_or_style.decompose()

        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        cleaned_text = '\n'.join(chunk for chunk in chunks if chunk)
        
        if len(cleaned_text.strip()) < 100:
             return None
             
        return cleaned_text

    except requests.exceptions.RequestException:
        return None