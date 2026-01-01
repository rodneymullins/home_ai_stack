"""Simplified scrapers for Pechanga, WinStar, and Seminole Hollywood"""
import re
import requests
from bs4 import BeautifulSoup
from dateutil import parser as dtp
from ..config import Config

# Pechanga
class Pechanga:
    casino = "Pechanga"
    property = "Pechanga Resort Casino"
    base_url = "https://blogs.pechanga.com/newsroom/tag/jackpot/"
    
    def fetch(self):
        # Similar pattern to Choctaw - filter newsroom by jackpot tag
        try:
            r = requests.get(self.base_url, headers={"User-Agent": Config.USER_AGENT}, timeout=Config.REQUEST_TIMEOUT)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "lxml")
            money_re = re.compile(r"\$([\d,]+(?:\.\d{2})?)")
            out = []
            # Extract article links and parse similar to Choctaw
            for a in soup.select('a[href*="/newsroom/"]')[:20]:
                href = a.get("href", "")
                if "https://" in href:
                    try:
                        p = requests.get(href, headers={"User-Agent": Config.USER_AGENT}, timeout=10)
                        ps = BeautifulSoup(p.text, "lxml")
                        body = ps.get_text()
                        m = money_re.search(body)
                        if m:
                            out.append({
                                "posted_date": None,
                                "amount": float(m.group(1).replace(",", "")),
                                "winner_name": None,
                                "game": None,
                                "location": None,
                                "source_url": href,
                                "raw": {},
                            })
                    except:
                        continue
            return out
        except:
            return []

# WinStar
class WinStar:
    casino = "WinStar"
    property = "WinStar World Casino"
    base_url = "https://www.winstar.com/gaming/"
    
    def fetch(self):
        # WinStar has unstructured data - minimal scraping
        return []  # Placeholder - returns empty for now

# Seminole Hollywood
class HardRockHollywood:
    casino = "Seminole Hard Rock"
    property = "Hollywood"
    base_url = "https://www.seminolehardrockhollywood.com/casino/jackpots"
    
    def fetch(self):
        # Similar to Tampa
        return []  # Placeholder
