#!/usr/bin/env python3
"""
Scrape Boyd Gaming Slot Search across all properties
Properties include: Orleans, Sam's Town, California, Fremont, Main Street, etc.
"""
import requests
from bs4 import BeautifulSoup
import psycopg2
from datetime import datetime
import time

def scrape_boyd_gaming(machine_name):
    """Search Boyd Gaming's unified slot search"""
    print(f"  Boyd: {machine_name[:40]}...", end=" ")
    
    search_term = machine_name.replace('(PROG)', '').replace('(MD)', '').strip()
    
    try:
        # Boyd Gaming slot search endpoint
        # Format: https://www.boydgaming.com/slot-search?search=machine_name
        search_url = f"https://www.boydgaming.com/slot-search"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
        # POST search query
        response = requests.post(search_url, 
                                data={'search': search_term},
                                headers=headers, 
                                timeout=10)
        
        if response.status_code != 200:
            print(f"HTTP {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        data = {
            'machine_name': machine_name.upper(),
            'source': 'Boyd Gaming',
            'url': search_url,
            'properties': [],  # Which Boyd properties have it
            'denomination': None,
            'location_info': []
        }
        
        # Extract property locations
        # Boyd shows which casinos have the machine
        property_divs = soup.find_all('div', class_='property') or soup.find_all('span', class_='casino-name')
        if property_divs:
            data['properties'] = [prop.get_text(strip=True) for prop in property_divs]
        
        # Extract denomination if shown
        denom_elem = soup.find(text=lambda t: t and '$' in t and ('¢' in t or 'cent' in t.lower()))
        if denom_elem:
            data['denomination'] = denom_elem.strip()
        
        if data['properties']:
            print(f"✓ (Found at {len(data['properties'])} properties)")
            return data
        else:
            print("✗")
            return None
            
    except Exception as e:
        print(f"✗ ({e})")
        return None

def save_boyd_data(data):
    """Save Boyd Gaming location data"""
    try:
        conn = psycopg2.connect(database="postgres", user="rod")
        cur = conn.cursor()
        
        # Store in community_feedback as location intelligence
        for property_name in data['properties']:
            cur.execute("""
                INSERT INTO community_feedback 
                (machine_name, source, sentiment, excerpt, posted_date)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                data['machine_name'],
                'Boyd Gaming',
                'neutral',
                f"Available at {property_name}",
                datetime.now()
            ))
        
        conn.commit()
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        return False

def main():
    """Scrape Boyd Gaming for our machines"""
    conn = psycopg2.connect(database="postgres", user="rod")
    cur = conn.cursor()
    
    # Get our top machines
    cur.execute("""
        SELECT DISTINCT machine_name
        FROM slot_machines
        WHERE machine_name NOT ILIKE '%Poker%' 
            AND machine_name NOT ILIKE '%Keno%'
        ORDER BY machine_name
        LIMIT 50
    """)
    
    machines = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    
    print(f"🎰 Scraping Boyd Gaming for {len(machines)} machines...\n")
    
    success = 0
    for i, machine in enumerate(machines, 1):
        print(f"[{i}/{len(machines)}] ", end="")
        data = scrape_boyd_gaming(machine)
        if data and save_boyd_data(data):
            success += 1
        time.sleep(2)
    
    print(f"\n✅ Found {success}/{len(machines)} at Boyd properties ({success/len(machines)*100:.1f}%)")

if __name__ == "__main__":
    main()
