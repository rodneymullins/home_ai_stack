"""Mohegan Sun scraper - newsroom category"""
import re
import requests
from bs4 import BeautifulSoup
from dateutil import parser as dtp
from ..config import Config

class MoheganJackpots:
    casino = "Mohegan Sun"
    property = "Mohegan Sun (CT)"
    base_url = "https://newsroom.mohegansun.com/category/jackpots/"

    def fetch(self):
        try:
            r = requests.get(self.base_url, headers={"User-Agent": Config.USER_AGENT}, timeout=Config.REQUEST_TIMEOUT)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "lxml")
            
            articles = soup.select("article a[href]")
            urls = []
            for a in articles:
                href = a.get("href", "")
                if href.startswith("https://newsroom.mohegansun.com/") and re.search(r"/\d{4}/\d{2}/\d{2}/", href):
                    urls.append(href)
            
            urls = list(dict.fromkeys(urls))[:200]  # Increased from 20 to collect more history
            out = []
            money_re = re.compile(r"\$([\d,]+(?:\.\d{2})?)")
            
            for url in urls:
                try:
                    p = requests.get(url, headers={"User-Agent": Config.USER_AGENT}, timeout=Config.REQUEST_TIMEOUT)
                    if p.status_code != 200:
                        continue
                    
                    ps = BeautifulSoup(p.text, "lxml")
                    title = (ps.select_one("h1") or ps.title).get_text(" ", strip=True)
                    body = ps.get_text("\n")
                    
                    time_el = ps.select_one("time")
                    posted_date = None
                    if time_el and time_el.get("datetime"):
                        posted_date = dtp.parse(time_el["datetime"]).date()
                    
                    m = money_re.search(body)
                    amount = float(m.group(1).replace(",", "")) if m else None
                    
                    out.append({
                        "posted_date": posted_date,
                        "amount": amount,
                        "winner_name": None,
                        "game": None,
                        "location": None,
                        "source_url": url,
                        "raw": {"title": title},
                    })
                except:
                    continue
            
            return out
        except Exception as e:
            print(f"Mohegan error: {e}")
            return []
