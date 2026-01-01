"""Foxwoods scraper - cleanest data source"""
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from ..config import Config

class FoxwoodsSlots:
    casino = "Foxwoods"
    property = "Foxwoods Resort Casino"
    base_url = "https://foxwoods.com/game/slots"

    def fetch(self):
        try:
            r = requests.get(self.base_url, headers={"User-Agent": Config.USER_AGENT}, timeout=Config.REQUEST_TIMEOUT)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "lxml")
            
            text = soup.get_text("\n")
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            out = []
            i = 0
            
            while i < len(lines) - 2:
                # Look for pattern: "Nov 30", "$25,533", "Name • Game"
                if re.match(r"^[A-Z][a-z]{2}\s+\d{1,2}$", lines[i]) and re.match(r"^\$[\d,]+", lines[i+1]):
                    dt = datetime.strptime(f"{lines[i]} {datetime.now().year}", "%b %d %Y").date()
                    amt = float(lines[i+1].replace("$","").replace(",",""))
                    name_game = lines[i+2]
                    
                    if "•" in name_game:
                        name, game = [x.strip() for x in name_game.split("•", 1)]
                    else:
                        name, game = None, name_game
                    
                    out.append({
                        "posted_date": dt,
                        "amount": amt,
                        "winner_name": name,
                        "game": game,
                        "location": None,
                        "source_url": self.base_url,
                        "raw": {"lines": [lines[i], lines[i+1], lines[i+2]]},
                    })
                    i += 3
                else:
                    i += 1
            
            return out  # Return all found jackpots (no limit)
        except Exception as e:
            print(f"Foxwoods error: {e}")
            return []
