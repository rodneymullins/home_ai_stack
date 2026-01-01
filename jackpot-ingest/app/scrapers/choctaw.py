"""Choctaw Durant scraper"""
import re
import requests
from bs4 import BeautifulSoup
from dateutil import parser as dtp
from ..config import Config

class ChoctawDurant:
    casino = "Choctaw"
    property = "Durant"
    base_url = "https://www.choctawcasinos.com/newsroom/"

    def fetch(self):
        try:
            r = requests.get(self.base_url, headers={"User-Agent": Config.USER_AGENT}, timeout=Config.REQUEST_TIMEOUT)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "lxml")
            
            urls = []
            for a in soup.select('a[href*="/newsroom/"]'):
                href = a.get("href","")
                if href.startswith("https://www.choctawcasinos.com/newsroom/") and href.count("/") > 4:
                    urls.append(href)
            
            urls = list(dict.fromkeys(urls))[:200]  # Collect maximum history
            out = []
            money_re = re.compile(r"\$([\d,]+(?:\.\d{2})?)")
            
            for url in urls:
                try:
                    p = requests.get(url, headers={"User-Agent": Config.USER_AGENT}, timeout=Config.REQUEST_TIMEOUT)
                    if p.status_code != 200:
                        continue
                    
                    ps = BeautifulSoup(p.text, "lxml")
                    title = (ps.select_one("h1") or ps.title).get_text(" ", strip=True)
                    t_low = title.lower()
                    
                    if not any(k in t_low for k in ["jackpot", "winner", "wins", "million", "grand"]):
                        continue
                    
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
            print(f"Choctaw error: {e}")
            return []
