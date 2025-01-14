import requests
import logging

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 監視したいURLリスト
URLS = [
    "https://yasuhiroiwai.jp",
    "https://yasu521.github.io",
]

def request_site(url):
    try:
        response = requests.get(url)
        logging.info(f"Requested {url}: Status Code {response.status_code}")
    except Exception as e:
        logging.error(f"Failed to request {url}: {e}")

def main():
    for url in URLS:
        request_site(url)

if __name__ == "__main__":
    main()
