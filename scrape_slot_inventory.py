#!/usr/bin/env python3
"""
Scrape and populate slot machine inventory from casino's API
"""
import requests
from bs4 import BeautifulSoup
import psycopg2
import re
from datetime import datetime
from config import DB_CONFIG

# Manufacturers to query
MANUFACTURERS = ["IGT", "Aristocrat", "Konami", "Scientific Games", "AGS", "Everi", "Ainsworth"]

def normalize_machine_name(title):
    """Normalize machine name to match jackpots table format"""
    # Remove extra whitespace
    name = ' '.join(title.split())
    # Convert to uppercase (jackpots table uses uppercase)
    name = name.upper()
    return name

def parse_slot_entry(entry_html):
    """Parse a slot machine entry from HTML response"""
    try:
        soup = BeautifulSoup(entry_html, 'html.parser')
        
        # Extract all text content
        text = soup.get_text()
        
        # Parse structured data using regex patterns
        machine_data = {}
        
        # Title pattern: "Title:MACHINE NAME"
        title_match = re.search(r'Title:\s*([^M]+?)(?:Manufacturer:|$)', text)
        if title_match:
            machine_data['machine_name'] = normalize_machine_name(title_match.group(1).strip())
        
        # Manufacturer
        manu_match = re.search(r'Manufacturer:\s*([^D]+?)(?:Denomination:|$)', text)
        if manu_match:
            machine_data['manufacturer'] = manu_match.group(1).strip()
        
        # Denomination
        denom_match = re.search(r'Denomination:\s*([^T]+?)(?:Type:|$)', text)
        if denom_match:
            machine_data['denomination'] = denom_match.group(1).strip()
        
        # Type
        type_match = re.search(r'Type:\s*([^V]+?)(?:Volatility:|$)', text)
        if type_match:
            machine_data['type'] = type_match.group(1).strip()
        
        # Volatility
        vol_match = re.search(r'Volatility:\s*(.+?)(?:\n|$)', text)
        if vol_match:
            machine_data['volatility'] = vol_match.group(1).strip()
        
        # Look for photo URL in img tags
        img_tag = soup.find('img')
        if img_tag and img_tag.get('src'):
            machine_data['photo_url'] = img_tag.get('src')
        
        # Look for map link
        map_link = soup.find('a', class_='lightbox-slot-map')
        if map_link and map_link.get('href'):
            machine_data['map_url'] = map_link.get('href')
        
        return machine_data if 'machine_name' in machine_data else None
        
    except Exception as e:
        print(f"Parse error: {e}")
        return None

def scrape_manufacturer_slots(manufacturer):
    """Scrape all slots for a given manufacturer"""
    url = f"https://www.coushattacasinoresort.com/ajax-slot-result-res.php?title=&denom=&manu={manufacturer}&type=&volatil="
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.coushattacasinoresort.com/gaming/slot-search/'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"❌ {manufacturer}: HTTP {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Each slot is in a table row
        rows = soup.find_all('tr')
        
        machines = []
        for row in rows:
            machine_data = parse_slot_entry(str(row))
            if machine_data:
                machines.append(machine_data)
        
        print(f"✓ {manufacturer}: {len(machines)} machines")
        return machines
        
    except Exception as e:
        print(f"❌ {manufacturer}: {e}")
        return []

def populate_database(machines):
    """Populate slot_machines table with scraped data"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        inserted = 0
        updated = 0
        errors = 0
        
        for machine in machines:
            try:
                # Upsert: insert or update if exists
                cur.execute("""
                    INSERT INTO slot_machines 
                    (machine_name, manufacturer, denomination, type, volatility, photo_url, map_url, last_updated)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (machine_name) 
                    DO UPDATE SET
                        manufacturer = EXCLUDED.manufacturer,
                        denomination = EXCLUDED.denomination,
                        type = EXCLUDED.type,
                        volatility = EXCLUDED.volatility,
                        photo_url = EXCLUDED.photo_url,
                        map_url = EXCLUDED.map_url,
                        last_updated = EXCLUDED.last_updated
                    RETURNING (xmax = 0) AS inserted
                """, (
                    machine.get('machine_name'),
                    machine.get('manufacturer'),
                    machine.get('denomination'),
                    machine.get('type'),
                    machine.get('volatility'),
                    machine.get('photo_url'),
                    machine.get('map_url'),
                    datetime.now()
                ))
                
                was_inserted = cur.fetchone()[0]
                conn.commit()  # Commit after each successful insert
                
                if was_inserted:
                    inserted += 1
                else:
                    updated += 1
                    
            except Exception as e:
                conn.rollback()  # Rollback this transaction and continue
                errors += 1
                if errors <= 5:  # Only print first 5 errors
                    print(f"Error for {machine.get('machine_name', 'unknown')}: {e}")
                continue
        
        if errors > 5:
            print(f"... and {errors - 5} more errors")
        
        cur.close()
        conn.close()
        
        return inserted, updated
        
    except Exception as e:
        print(f"Database connection error: {e}")
        return 0, 0

def main():
    print("🎰 Starting slot machine inventory scrape...\n")
    
    all_machines = []
    
    for manufacturer in MANUFACTURERS:
        machines = scrape_manufacturer_slots(manufacturer)
        all_machines.extend(machines)
    
    print(f"\n📊 Total machines scraped: {len(all_machines)}")
    
    if all_machines:
        print("\n💾 Populating database...")
        inserted, updated = populate_database(all_machines)
        print(f"✅ Inserted: {inserted} | Updated: {updated}")
    else:
        print("⚠️ No machines to insert")

if __name__ == "__main__":
    main()
