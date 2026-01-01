#!/usr/bin/env python3
"""
Scraper for IGT Jackpots Library - official progressive jackpot data
URL: https://www.igtjackpots.com
"""
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime

def scrape_igt_jackpots_library():
    """Scrape IGT's official jackpot library for historical wins"""
    url = "https://www.igtjackpots.com"
    
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        
        # Look for jackpot winner listings
        jackpots = []
        
        # IGT typically shows recent winners in a feed/table
        # Find all jackpot entries
        winners = soup.find_all(class_=re.compile(r'jackpot|winner|prize', re.I))
        
        money_re = re.compile(r'\$?([\d,]+(?:\.\d{2})?)')
        
        for winner in winners:
            text = winner.get_text()
            
            # Extract amount
            match = money_re.search(text)
            if match:
                amount = float(match.group(1).replace(',', ''))
                
                # Extract game name if present
                game = "IGT Progressive"
                if 'megabucks' in text.lower():
                    game = "Megabucks"
                elif 'wheel' in text.lower():
                    game = "Wheel of Fortune"
                
                jackpots.append({
                    'casino': 'IGT Network',
                    'machine_name': game,
                    'amount': amount,
                    'date_text': None,
                    'source_url': url
                })
        
        print(f"IGT Jackpots: Found {len(jackpots)} progressive wins")
        return jackpots
        
    except Exception as e:
        print(f"IGT scraper error: {e}")
        return []

if __name__ == "__main__":
    jackpots = scrape_igt_jackpots_library()
    for jp in jackpots[:10]:
        print(f"  {jp['machine_name']}: ${jp['amount']:,.2f}")
