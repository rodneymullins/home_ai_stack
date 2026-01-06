#!/usr/bin/env python3
"""
Scrape URComped Slot Machine Finder - community-driven platform
URL: https://www.urcomped.com/slot-machine-finder
3,000+ machines with photos, videos, and casino locations
"""
import requests
from bs4 import BeautifulSoup
import psycopg2
from datetime import datetime
import time

def scrape_urcomped_search(machine_name):
    """Search URComped for machine details and locations"""
    print(f"  URComped: {machine_name[:40]}...", end=" ")
    
    search_term = machine_name.replace('(PROG)', '').replace('(MD)', '').strip()
    
    try:
        # URComped slot finder search
        search_url = f"https://www.urcomped.com/slot-machine-finder?search={search_term}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
        response = requests.get(search_url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"HTTP {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # URComped provides:
        # - Machine photos/videos
        # - Casino locations where it's found
        # - Player reviews and comments
        # - Game type and features
        
        data = {
            'machine_name': machine_name.upper(),
            'source': 'URComped',
            'url': search_url,
            'casinos': [],  # List of casinos that have this machine
            'photo_urls': [],
            'video_urls': [],
            'features': []
        }
        
        # Extract casino locations (example selector - adjust based on actual page)
        casino_elements = soup.select('.casino-location') or soup.find_all(text=lambda t: t and 'casino' in t.lower())
        if casino_elements:
            data['casinos'] = [elem.get_text(strip=True) for elem in casino_elements[:5]]
        
        # Extract photo URLs
        images = soup.find_all('img', src=lambda s: s and 'slot' in s.lower())
        if images:
            data['photo_urls'] = [img['src'] for img in images[:3]]
        
        # Extract features from description
        description = soup.find('div', class_='description') or soup.find('div', class_='game-info')
        if description:
            desc_text = description.get_text()
            feature_keywords = ['Free Spins', 'Wild', 'Multiplier', 'Progressive', 'Bonus', 'Scatter']
            found_features = [f for f in feature_keywords if f.lower() in desc_text.lower()]
            if found_features:
                data['features'] = found_features
        
        if data['casinos'] or data['photo_urls'] or data['features']:
            print(f"✓ ({len(data['casinos'])} casinos, {len(data['photo_urls'])} photos)")
            return data
        else:
            print("✗ (not found)")
            return None
            
    except Exception as e:
        print(f"✗ ({e})")
        return None

def save_urcomped_data(data):
    """Save URComped data to database"""
    try:
        conn = get_db_connection()
        if not conn:
            print("❌ Database connection failed")
            return 0
        cur = conn.cursor()
        
        # Update machine_specs with URComped data
        cur.execute("""
            INSERT INTO machine_specs 
            (machine_name, features, source, spec_url, last_updated)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (machine_name) DO UPDATE SET
                features = CASE 
                    WHEN EXCLUDED.features IS NOT NULL AND array_length(EXCLUDED.features, 1) > 0 
                    THEN EXCLUDED.features 
                    ELSE machine_specs.features 
                END,
                source = COALESCE(machine_specs.source || ', ' || EXCLUDED.source, EXCLUDED.source),
                last_updated = EXCLUDED.last_updated
        """, (
            data['machine_name'],
            data['features'],
            data['source'],
            data['url'],
            datetime.now()
        ))
        
        # Store photo URLs in slot_machines table if we found better ones
        if data['photo_urls']:
            cur.execute("""
                UPDATE slot_machines 
                SET photo_url = %s
                WHERE machine_name = %s AND (photo_url IS NULL OR photo_url = '')
            """, (data['photo_urls'][0], data['machine_name']))
        
        conn.commit()
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"  DB Error: {e}")
        return False

def main():
    """Scrape URComped for our top machines"""
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return
    cur = conn.cursor()
    
    # Get top machines by jackpot frequency
    cur.execute("""
        SELECT DISTINCT m.machine_name, COUNT(j.id) as hits
        FROM slot_machines m
        LEFT JOIN jackpots j ON m.machine_name = j.machine_name
        WHERE m.machine_name NOT ILIKE '%Poker%' 
            AND m.machine_name NOT ILIKE '%Keno%'
        GROUP BY m.machine_name
        HAVING COUNT(j.id) > 10
        ORDER BY COUNT(j.id) DESC
        LIMIT 100
    """)
    
    machines = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    
    print(f"🔍 Scraping URComped for {len(machines)} popular machines...")
    print(f"⏱️  Estimated time: {len(machines) * 2 / 60:.1f} minutes\n")
    
    success = 0
    for i, machine in enumerate(machines, 1):
        print(f"[{i}/{len(machines)}] ", end="")
        data = scrape_urcomped_search(machine)
        if data and save_urcomped_data(data):
            success += 1
        time.sleep(2)  # Be polite
        
        if i % 25 == 0:
            print(f"\n📊 Progress: {success}/{i} found\n")
    
    print(f"\n{'='*60}")
    print(f"✅ Found data for {success}/{len(machines)} machines ({success/len(machines)*100:.1f}%)")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
