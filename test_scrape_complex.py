
import threading
import requests
import time
from bs4 import BeautifulSoup
import pandas as pd
import psycopg2
from flask import Flask
from pytrends.request import TrendReq
import feedparser

print("Complex Test: Imported ALL libs (Flask, Pytrends, etc). Starting thread.")

def scrape():
    print("Thread: Starting request...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    }
    try:
        r = requests.get("https://www.coushattacasinoresort.com/gaming/slot-jackpot-updates/page/1", headers=headers, timeout=15)
        print(f"Thread: Status {r.status_code}")
    except Exception as e:
        print(f"Thread Error: {e}")

t = threading.Thread(target=scrape)
t.start()
t.join()
print("Done.")
