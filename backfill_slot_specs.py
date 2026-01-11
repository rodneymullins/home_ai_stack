#!/usr/bin/env python3
"""
Backfill Missing Slot Machine Specs from Coushatta API
Fills in missing machine_specs data for slot_machines entries
"""

import requests
from bs4 import BeautifulSoup
import psycopg2
from datetime import datetime
import time

# Coushatta slot search API endpoint
API_URL = "https://www.coushattacasinoresort.com/ajax-slot-result-res.php?title=&denom=&manu=&type=&volatil="

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Referer': 'https://www.coushattacasinoresort.com/gaming/slot-search/'
}

DB_CONFIG = {'database': 'postgres', 'user': 'rod', 'host': '192.168.1.211'}

def get_db():
    return psycopg2.connect(**DB_CONFIG)

def fetch_all_machines_from_api():
    """Fetch all machines from Coushatta API"""
    print("🔍 Fetching all machines from Coushatta API...")
    
    r = requests.get(API_URL, headers=HEADERS, timeout=15)
    
    if r.status_code != 200:
        print(f"❌ API returned status {r.status_code}")
        return []
    
    soup = BeautifulSoup(r.text, 'html.parser')
    
    # Parse table rows
    rows = soup.find_all('tr')
    machines = []
    
    for row in rows:
        cells = row.find_all('td')
        if len(cells) >= 5:  # Expected: Name, Denom, Manufacturer, Type, Volatility
            try:
                machine = {
                    'name': cells[0].get_text(strip=True),
                    'denomination': cells[1].get_text(strip=True),
                    'manufacturer': cells[2].get_text(strip=True),
                    'game_type': cells[3].get_text(strip=True),
                    'volatility': cells[4].get_text(strip=True)
                }
                
                if machine['name']:  # Only add if has name
                    machines.append(machine)
            except Exception as e:
                continue
    
    print(f"✅ Found {len(machines)} machines from API")
    return machines

def get_missing_machines():
    """Get machines that don't have specs"""
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT DISTINCT sm.machine_name 
        FROM slot_machines sm 
        LEFT JOIN machine_specs ms ON sm.machine_name = ms.machine_name 
        WHERE ms.machine_name IS NULL
    """)
    
    missing = [row[0] for row in cur.fetchall()]
    
    cur.close()
    conn.close()
    
    return missing

def normalize_name(name):
    """Normalize machine name for matching"""
    return name.upper().strip().replace('  ', ' ')

def backfill_specs():
    """Backfill missing specs from API data"""
    
    # Get API data
    api_machines = fetch_all_machines_from_api()
    if not api_machines:
        print("❌ No data from API")
        return
    
    # Create lookup dict (normalized name -> machine data)
    api_lookup = {}
    for machine in api_machines:
        norm_name = normalize_name(machine['name'])
        api_lookup[norm_name] = machine
    
    # Get missing machines from DB
    missing = get_missing_machines()
    print(f"📋 Found {len(missing)} machines without specs")
    
    if not missing:
        print("✅ All machines already have specs!")
        return
    
    # Match and insert
    conn = get_db()
    cur = conn.cursor()
    
    filled = 0
    not_found = 0
    
    for db_name in missing:
        norm_db_name = normalize_name(db_name)
        
        # Try exact match
        if norm_db_name in api_lookup:
            api_data = api_lookup[norm_db_name]
            
            try:
                # Parse features (volatility as feature)
                features = []
                if api_data['volatility']:
                    features.append(f"Volatility: {api_data['volatility']}")
                if api_data['game_type']:
                    features.append(api_data['game_type'])
                
                cur.execute("""
                    INSERT INTO machine_specs (
                        machine_name, features, source, last_updated
                    ) VALUES (%s, %s, %s, NOW())
                    ON CONFLICT (machine_name) DO NOTHING
                """, (
                    db_name,
                    features if features else None,
                    'coushatta_api'
                ))
                
                filled += 1
                if filled % 50 == 0:
                    print(f"   Progress: {filled} filled...")
                
            except Exception as e:
                print(f"❌ Error inserting {db_name}: {e}")
        else:
            not_found += 1
    
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"\n✅ Backfill complete!")
    print(f"   Filled: {filled}")
    print(f"   Not found in API: {not_found}")
    print(f"   Total processed: {len(missing)}")

if __name__ == "__main__":
    print("=" * 60)
    print("Slot Machine Specs Backfill")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    backfill_specs()
