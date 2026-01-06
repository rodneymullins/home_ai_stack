#!/usr/bin/env python3
"""
Scrape IGT spec sheets for machine RTP% and features
"""
import requests
from bs4 import BeautifulSoup
import psycopg2
from datetime import datetime
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils.db_pool import get_db_connection

def scrape_igt_machine(machine_name):
    """
    Attempt to find IGT spec sheet for a machine
    IGT website structure: https://www.igt.com/explore-games
    """
    print(f"\n Searching IGT for: {machine_name}")
    
    # Clean machine name for search
    search_term = machine_name.replace('(PROG)', '').replace('(MD)', '').strip()
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    
    try:
        # IGT game search endpoint (may need adjustment based on actual site structure)
        search_url = f"https://www.igt.com/us-en/search?q={search_term}"
        
        response = requests.get(search_url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"  ❌ HTTP {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for game spec data (this is a template - actual selectors will vary)
        # Example structure to look for:
        # <div class="rtp">95.5%</div>
        # <span class="feature">Free Spins</span>
        
        spec_data = {
            'machine_name': machine_name.upper(),
            'source': 'IGT',
            'spec_url': search_url,
            'rtp_percentage': None,
            'features': [],
            'theme': None
        }
        
        # Try to extract RTP (example selectors - adjust based on actual site)
        rtp_elem = soup.find(text=lambda t: t and 'RTP' in t)
        if rtp_elem:
            # Extract percentage from text like "RTP: 95.5%"
            import re
            rtp_match = re.search(r'(\d+\.?\d*)%', str(rtp_elem))
            if rtp_match:
                spec_data['rtp_percentage'] = float(rtp_match.group(1))
                print(f"  ✓ Found RTP: {spec_data['rtp_percentage']}%")
        
        # Extract features
        feature_keywords = ['Free Spins', 'Wild', 'Multiplier', 'Bonus', 'Progressive', 'Scatter']
        page_text = soup.get_text()
        found_features = [f for f in feature_keywords if f.lower() in page_text.lower()]
        if found_features:
            spec_data['features'] = found_features
            print(f"  ✓ Found features: {', '.join(found_features)}")
        
        return spec_data if spec_data['rtp_percentage'] or spec_data['features'] else None
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return None

def save_spec_to_db(spec):
    """Save spec data to database"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO machine_specs 
            (machine_name, rtp_percentage, features, source, spec_url, last_updated)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (machine_name) DO UPDATE SET
                rtp_percentage = EXCLUDED.rtp_percentage,
                features = EXCLUDED.features,
                spec_url = EXCLUDED.spec_url,
                last_updated = EXCLUDED.last_updated
        """, (
            spec['machine_name'],
            spec['rtp_percentage'],
            spec['features'],
            spec['source'],
            spec['spec_url'],
            datetime.now()
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"  DB Error: {e}")
        return False

def main():
    """Scrape specs for ALL IGT machines in our database"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get ALL IGT machines (no limit)
    cur.execute("""
        SELECT DISTINCT machine_name 
        FROM slot_machines 
        WHERE manufacturer = 'IGT'
        ORDER BY machine_name
    """)
    
    machines = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    
    print(f"🔍 Scraping IGT specs for {len(machines)} machines...")
    print(f"⏱️  Estimated time: {len(machines) * 2 / 60:.1f} minutes (2s delay per machine)\n")
    
    success_count = 0
    error_count = 0
    
    for i, machine in enumerate(machines, 1):
        print(f"[{i}/{len(machines)}] {machine[:40]}...", end=" ")
        spec = scrape_igt_machine(machine)
        if spec:
            if save_spec_to_db(spec):
                success_count += 1
                print("✓")
            else:
                error_count += 1
                print("✗ (DB error)")
        else:
            error_count += 1
            print("✗ (Not found)")
        
        time.sleep(2)  # Be polite to IGT servers
        
        # Progress report every 50 machines
        if i % 50 == 0:
            print(f"\n📊 Progress: {success_count} success, {error_count} errors\n")
    
    print(f"\n{'='*60}")
    print(f"✅ Successfully scraped {success_count}/{len(machines)} machine specs")
    print(f"❌ Errors: {error_count}")
    print(f"📈 Success rate: {success_count/len(machines)*100:.1f}%")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
