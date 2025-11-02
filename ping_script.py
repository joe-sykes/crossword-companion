import requests
import logging
from datetime import datetime

def ping_endpoints():
    endpoints = [
        "https://crossword-companion.net",  # ✅ your frontend
        "https://crossword-companion.onrender.com"  # ✅ your backend (adjust if needed)
    ]
    
    for url in endpoints:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                logging.info(f"{datetime.now()} - ✅ Pinged {url} successfully")
            else:
                logging.warning(f"{datetime.now()} - ⚠️ {url} returned {response.status_code}")
        except Exception as e:
            logging.error(f"{datetime.now()} - ❌ Error pinging {url}: {e}")

def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ping_endpoints()

if __name__ == "__main__":
    main()
