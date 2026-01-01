#!/usr/bin/env python3
"""
Casino.org Progressive Jackpot Tracker Scraper
Real-time and historical progressive jackpot data
"""
import requests
from bs4 import BeautifulSoup
import re

def scrape_casino_org_jackpots():
    """Scrape Casino.org's progressive jackpot tracker"""
    url = "https://www.casino.org/progressive-jackpots/"
    
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        
        jackpots = []
        money_re = re.compile(r'\$?([\d,]+(?:\.\d{2})?)')
        
        # Look for jackpot tables/listings
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows[1:]:  # Skip header
                cols = row.find_all(['td', 'th'])
                if len(cols) >= 2:
                    game_name = cols[0].get_text(strip=True)
                    amount_text = cols[1].get_text(strip=True)
                    
                    match = money_re.search(amount_text)
                    if match:
                        amount = float(match.group(1).replace(',', ''))
                        
                        jackpots.append({
                            'casino': 'Online Progressive',
                            'machine_name': game_name,
                            'amount': amount,
                            'date_text': None,
                            'source_url': url
                        })
        
        print(f"Casino.org: Found {len(jackpots)} progressive jackpots")
        return jackpots
        
    except Exception as e:
        print(f"Casino.org scraper error: {e}")
        return []

if __name__ == "__main__":
    jackpots = scrape_casino_org_jackpots()
    for jp in jackpots[:10]:
        print(f"  {jp['machine_name']}: ${jp['amount']:,.2f}")
