#!/usr/bin/env python3
"""
Comprehensive USA Slot Manufacturer Scraper
Covers ALL major manufacturers with games in USA casinos
"""
import requests
from bs4 import BeautifulSoup
import psycopg2
from datetime import datetime
import time
import re
import sys

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
}

def get_db_connection():
    """Try multiple connection methods for PostgreSQL"""
    configs = [
        {'database': "postgres", 'user': "rod"},  # Standard local socket
        {'database': "postgres", 'user': "rod", 'host': "localhost"},
        {'database': "postgres", 'user': "rod", 'host': "127.0.0.1"},
        {'database': "postgres", 'user': "rod", 'host': "192.168.1.211"}  # Thor's actual IP
    ]
    
    for config in configs:
        try:
            conn = psycopg2.connect(**config, connect_timeout=3)
            return conn
        except:
            continue
            
    print("❌ Could not connect to any PostgreSQL database (socket, localhost, or 192.168.1.211)")
    return None

# ========== SCIENTIFIC GAMES / LIGHT & WONDER ==========
def scrape_scientific_games(machine_name):
    """Light & Wonder (formerly Scientific Games, WMS, Bally, Shuffle Master)"""
    print(f"  SG/L&W: {machine_name[:35]}...", end=" ")
    
    search_term = machine_name.replace('(PROG)', '').replace('(MD)', '').strip()
    
    try:
        # Light & Wonder game catalog
        # Use lnw.com instead of www.lnw.com which fails DNS
        url = f"https://lnw.com/games/our-games?search={search_term}"
        response = requests.get(url, headers=HEADERS, timeout=10)
        
        if response.status_code != 200:
            print(f"HTTP {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for game details
        game_card = soup.find('div', class_='game-card') or soup.find('div', class_='product')
        if not game_card:
            print("✗")
            return None
        
        data = {
            'machine_name': machine_name.upper(),
            'source': 'Light & Wonder',
            'url': url,
            'features': [],
            'rtp_percentage': None
        }
        
        # Extract RTP if available
        text = soup.get_text()
        rtp_match = re.search(r'RTP[:\s]+(\d+\.?\d*)%', text, re.IGNORECASE)
        if rtp_match:
            data['rtp_percentage'] = float(rtp_match.group(1))
        
        # Extract features
        feature_keywords = ['Free Spins', 'Wild', 'Multiplier', 'Progressive', 'Bonus', 'Scatter', 'Respins']
        found = [f for f in feature_keywords if f.lower() in text.lower()]
        if found:
            data['features'] = found
        
        if data['features'] or data['rtp_percentage']:
            print(f"✓ (RTP: {data['rtp_percentage']}%)" if data['rtp_percentage'] else "✓")
            return data
        print("✗")
        return None
        
    except Exception as e:
        print(f"✗ ({str(e)[:20]})")
        return None

# ========== ARUZE GAMING ==========
def scrape_aruze(machine_name):
    """Aruze Gaming (Japanese manufacturer, US market)"""
    print(f"  Aruze: {machine_name[:35]}...", end=" ")
    
    search_term = machine_name.replace('(PROG)', '').strip()
    
    try:
        # Aruze Global seems to be the current site
        url = f"https://aruzeglobal.com/?s={search_term}" 
        response = requests.get(url, headers=HEADERS, timeout=10)
        
        if response.status_code != 200:
            print(f"HTTP {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        text = soup.get_text()
        
        data = {
            'machine_name': machine_name.upper(),
            'source': 'Aruze',
            'url': url,
            'features': []
        }
        
        features = ['Free Games', 'Wild', 'Bonus', 'Progressive']
        found = [f for f in features if f.lower() in text.lower()]
        
        if found:
            data['features'] = found
            print(f"✓ ({len(found)} features)")
            return data
        print("✗")
        return None
        
    except Exception as e:
        print(f"✗ ({str(e)[:20]})")
        return None

# ========== VGT (Video Gaming Technologies) ==========
def scrape_vgt(machine_name):
    """VGT - Major Class II/III manufacturer"""
    print(f"  VGT: {machine_name[:35]}...", end=" ")
    
    search_term = machine_name.replace('(PROG)', '').strip()
    
    try:
        url = f"https://www.videogamingtechnologies.com/games?search={search_term}"
        response = requests.get(url, headers=HEADERS, timeout=10)
        
        if response.status_code != 200:
            print(f"HTTP {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        text = soup.get_text()
        
        data = {
            'machine_name': machine_name.upper(),
            'source': 'VGT',
            'url': url,
            'features': []
        }
        
        features = ['Free Spins', 'Pick Bonus', 'Wild', 'Progressive']
        found = [f for f in features if f.lower() in text.lower()]
        
        if found:
            data['features'] = found
            print(f"✓")
            return data
        print("✗")
        return None
        
    except Exception as e:
        print(f"✗ ({str(e)[:20]})")
        return None

# ========== INCREDIBLE TECHNOLOGIES ==========
def scrape_incredible_tech(machine_name):
    """IT - Creator of Game King video poker"""
    print(f"  IT: {machine_name[:35]}...", end=" ")
    
    search_term = machine_name.replace('(PROG)', '').strip()
    
    try:
        url = f"https://www.itsgames.com/games?q={search_term}"
        response = requests.get(url, headers=HEADERS, timeout=10)
        
        if response.status_code != 200:
            print(f"HTTP {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        text = soup.get_text()
        
        data = {
            'machine_name': machine_name.upper(),
            'source': 'Incredible Technologies',
            'url': url,
            'features': []
        }
        
        if 'game king' in text.lower() or 'video poker' in text.lower():
            data['features'] = ['Video Poker']
            print("✓")
            return data
        print("✗")
        return None
        
    except Exception as e:
        print(f"✗ ({str(e)[:20]})")
        return None

# ========== NEVADA GAMING CONTROL BOARD ==========
def scrape_nevada_gaming(machine_name):
    """Nevada Gaming Control Board - Official approved games list with RTP%"""
    print(f"  NV Gaming: {machine_name[:30]}...", end=" ")
    
    search_term = machine_name.replace('(PROG)', '').strip()
    
    try:
        # Nevada Gaming publishes approved game lists
        url = "https://gaming.nv.gov/index.aspx?page=51"
        
        # This would need to download their Excel/PDF files and parse them
        # For now, structure the data model
        
        data = {
            'machine_name': machine_name.upper(),
            'source': 'Nevada Gaming Control Board',
            'url': url,
            'rtp_percentage': None,
            'approval_number': None
        }
        
        # TODO: Download and parse official game approval documents
        print("⏭️ (requires PDF parsing)")
        return None
        
    except Exception as e:
        print(f"✗ ({str(e)[:20]})")
        return None

def save_spec_to_db(spec):
    """Save manufacturer spec data"""
    try:
        conn = get_db_connection()
        if not conn:
            return False
            
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO machine_specs 
            (machine_name, rtp_percentage, features, source, spec_url, last_updated)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (machine_name) DO UPDATE SET
                rtp_percentage = COALESCE(EXCLUDED.rtp_percentage, machine_specs.rtp_percentage),
                features = CASE 
                    WHEN EXCLUDED.features IS NOT NULL AND array_length(EXCLUDED.features, 1) > 0 
                    THEN EXCLUDED.features 
                    ELSE machine_specs.features 
                END,
                source = COALESCE(machine_specs.source || ', ' || EXCLUDED.source, EXCLUDED.source),
                last_updated = EXCLUDED.last_updated
        """, (
            spec['machine_name'],
            spec.get('rtp_percentage'),
            spec.get('features'),
            spec['source'],
            spec['url'],
            datetime.now()
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"DB Error: {e}")
        return False

def main():
    """Scrape all USA manufacturers"""
    print("Testing DB connection...")
    conn = get_db_connection()
    if not conn:
        print("❌ Cannot start scraper - no database connection")
        sys.exit(1)
        
    cur = conn.cursor()
    
    # Manufacturers to scrape
    manufacturers = [
        ('Scientific Games', scrape_scientific_games),
        ('Aruze', scrape_aruze),
        ('VGT', scrape_vgt),
        ('Incredible Technologies', scrape_incredible_tech),
    ]
    
    try:
        # Get sample machines for testing
        cur.execute("""
            SELECT DISTINCT machine_name 
            FROM slot_machines 
            WHERE machine_name NOT ILIKE '%Poker%' 
                AND machine_name NOT ILIKE '%Keno%'
            ORDER BY machine_name
            LIMIT 50
        """)
        
        machines = [row[0] for row in cur.fetchall()]
    except Exception as e:
        print(f"❌ Error fetching machines: {e}")
        machines = []
        
    cur.close()
    conn.close()
    
    print(f"🏭 Scraping {len(manufacturers)} additional USA manufacturers")
    print(f"Testing with {len(machines)} machines\n")
    
    total_success = 0
    
    for mfg_name, scraper_func in manufacturers:
        print(f"\n{'='*70}")
        print(f"🎰 {mfg_name.upper()}")
        print(f"{'='*70}\n")
        
        success = 0
        for machine in machines:
            spec = scraper_func(machine)
            if spec and save_spec_to_db(spec):
                success += 1
            time.sleep(1.5)
        
        total_success += success
        print(f"\n{mfg_name}: {success}/{len(machines)} found ({success/len(machines)*100:.1f}%)\n")
    
    print(f"\n{'='*70}")
    print(f"📊 TOTAL: {total_success} specs across all manufacturers")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
