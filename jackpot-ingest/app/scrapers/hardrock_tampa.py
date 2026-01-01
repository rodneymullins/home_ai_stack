"""Seminole Hard Rock Tampa scraper"""
import re
import requests
from bs4 import BeautifulSoup
from dateutil import parser as dtp
from ..config import Config

class HardRockTampa:
    casino = "Seminole Hard Rock"
    property = "Tampa"
    base_url = "https://casino.hardrock.com/tampa/newsroom"

    def fetch(self):
        try:
            r = requests.get(self.base_url, headers={"User-Agent": Config.USER_AGENT}, timeout=Config.REQUEST_TIMEOUT)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "lxml")
            
            links = []
            for a in soup.select('a[href*="/tampa/newsroom/"]'):
                href = a.get("href","")
                if href.startswith("https://"):
                    links.append(href)
                elif href.startswith("/"):
                    links.append("https://casino.hardrock.com" + href)
            
            links = [u for u in dict.fromkeys(links) if "jackpot" in u.lower()][:200]  # Increased for deeper history
            money_re = re.compile(r"\$([\d,]+(?:\.\d{2})?)")
            out = []
            
            for url in links:
                try:
                    p = requests.get(url, headers={"User-Agent": Config.USER_AGENT}, timeout=Config.REQUEST_TIMEOUT)
                    if p.status_code != 200:
                        continue
                    
                    ps = BeautifulSoup(p.text, "lxml")
                    title = (ps.select_one("h1") or ps.title).get_text(" ", strip=True)
                    body = ps.get_text("\n")
                    
                    posted_date = None
                    time_el = ps.select_one("time")
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
            print(f"Hard Rock Tampa error: {e}")
            return []
