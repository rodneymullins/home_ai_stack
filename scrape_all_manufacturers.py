#!/usr/bin/env python3
"""
Comprehensive multi-manufacturer spec scraper
Scrapes ALL manufacturers: IGT, Aristocrat, Konami, Everi, AGS, Ainsworth
"""
import requests
from bs4 import BeautifulSoup
import psycopg2
from datetime import datetime
import time
import re
import sys
import os

# Add parent directory to path to find utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from utils.db_pool import get_db_connection
except ImportError:
    # Fallback if utils not found
    import psycopg2
    from psycopg2.extras import RealDictCursor
    print("⚠️  Warning: utils.db_pool not found. Using direct connection.")
    def get_db_connection():
        return psycopg2.connect("dbname=postgres user=rod", cursor_factory=RealDictCursor)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def scrape_aristocrat_machine(machine_name):
    """Scrape Aristocrat product catalog"""
    print(f"  Aristocrat: {machine_name[:40]}...", end=" ")
    
    search_term = machine_name.replace('(PROG)', '').replace('(MD)', '').replace('(P)', '').strip()
    
    try:
        # Aristocrat gaming products catalog
        search_url = f"https://aristocratgaming.com/products/?s={search_term}"
        
        response = requests.get(search_url, headers=HEADERS, timeout=10)
        
        if response.status_code != 200:
            print(f"HTTP {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        spec_data = {
            'machine_name': machine_name.upper(),
            'source': 'Aristocrat',
            'spec_url': search_url,
            'rtp_percentage': None,
            'features': [],
            'theme': None
        }
        
        # Look for RTP
        page_text = soup.get_text()
        rtp_match = re.search(r'RTP[:\s]+(\d+\.?\d*)%', page_text, re.IGNORECASE)
        if rtp_match:
            spec_data['rtp_percentage'] = float(rtp_match.group(1))
        
        # Extract features
        feature_keywords = ['Free Games', 'Wild', 'Reel Power', 'Multiplier', 'Bonus', 'Progressive']
        found_features = [f for f in feature_keywords if f.lower() in page_text.lower()]
        if found_features:
            spec_data['features'] = found_features
        
        if spec_data['rtp_percentage'] or spec_data['features']:
            print(f"✓ (RTP: {spec_data['rtp_percentage']}%)" if spec_data['rtp_percentage'] else "✓")
            return spec_data
        else:
            print("✗")
            return None
            
    except Exception as e:
        print(f"✗ ({e})")
        return None

def scrape_konami_machine(machine_name):
    """Scrape Konami gaming products"""
    print(f"  Konami: {machine_name[:40]}...", end=" ")
    
    search_term = machine_name.replace('(PROG)', '').replace('(MD)', '').strip()
    
    try:
        # Konami gaming site
        search_url = f"https://www.konamigaming.com/games/?search={search_term}"
        
        response = requests.get(search_url, headers=HEADERS, timeout=10)
        
        if response.status_code != 200:
            print(f"HTTP {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        spec_data = {
            'machine_name': machine_name.upper(),
            'source': 'Konami',
            'spec_url': search_url,
            'rtp_percentage': None,
            'features': [],
        }
        
        page_text = soup.get_text()
        
        # Look for volatility and features
        feature_keywords = ['Free Spins', 'Action Stacked', 'Balance of Fortune', 'Bonus', 'Wild']
        found_features = [f for f in feature_keywords if f.lower() in page_text.lower()]
        if found_features:
            spec_data['features'] = found_features
            print(f"✓ ({len(found_features)} features)")
            return spec_data
        else:
            print("✗")
            return None
            
    except Exception as e:
        print(f"✗ ({e})")
        return None

def scrape_everi_machine(machine_name):
    """Scrape Everi (formerly Bally/WMS) specs"""
    print(f"  Everi: {machine_name[:40]}...", end=" ")
    
    search_term = machine_name.replace('(PROG)', '').replace('(MD)', '').strip()
    
    try:
        search_url = f"https://everi.com/games/?s={search_term}"
        
        response = requests.get(search_url, headers=HEADERS, timeout=10)
        
        if response.status_code != 200:
            print(f"HTTP {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        spec_data = {
            'machine_name': machine_name.upper(),
            'source': 'Everi',
            'spec_url': search_url,
            'rtp_percentage': None,
            'features': [],
        }
        
        page_text = soup.get_text()
        feature_keywords = ['Free Games', 'Wild', 'Multiplier', 'Jackpot', 'Progressive']
        found_features = [f for f in feature_keywords if f.lower() in page_text.lower()]
        
        if found_features:
            spec_data['features'] = found_features
            print(f"✓ ({len(found_features)} features)")
            return spec_data
        else:
            print("✗")
            return None
            
    except Exception as e:
        print(f"✗ ({e})")
        return None

def scrape_ags_machine(machine_name):
    """Scrape AGS (American Gaming Systems) specs"""
    print(f"  AGS: {machine_name[:40]}...", end=" ")
    
    search_term = machine_name.replace('(PROG)', '').replace('(MD)', '').strip()
    
    try:
        search_url = f"https://www.playags.com/games?search={search_term}"
        
        response = requests.get(search_url, headers=HEADERS, timeout=10)
        
        if response.status_code != 200:
            print(f"HTTP {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        spec_data = {
            'machine_name': machine_name.upper(),
            'source': 'AGS',
            'spec_url': search_url,
            'rtp_percentage': None,
            'features': [],
        }
        
        page_text = soup.get_text()
        feature_keywords = ['Free Games', 'Wild', 'Bonus', 'Progressive', 'Jackpot']
        found_features = [f for f in feature_keywords if f.lower() in page_text.lower()]
        
        if found_features:
            spec_data['features'] = found_features
            print(f"✓ ({len(found_features)} features)")
            return spec_data
        else:
            print("✗")
            return None
            
    except Exception as e:
        print(f"✗ ({e})")
        return None

def save_spec_to_db(spec):
    """Save spec data to database"""
    conn = get_db_connection()
    if not conn:
        return False
        
    try:
        with conn.cursor() as cur:
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
            return True
        
    except Exception as e:
        print(f"Error saving spec: {e}")
        return False
    finally:
        conn.close()

def main():
    """Scrape ALL manufacturers"""
    # Use context manager for main connection
    conn = get_db_connection()
    if not conn:
        print("❌ DB Connection failed")
        return

    try:
        with conn.cursor() as cur:
            # Get machines grouped by manufacturer
            manufacturers = {
                'Aristocrat': scrape_aristocrat_machine,
                'Konami': scrape_konami_machine,
                'Everi': scrape_everi_machine,
                'AGS': scrape_ags_machine
            }
            
            total_success = 0
            total_attempted = 0
            
            for mfg_name, scraper_func in manufacturers.items():
                print(f"\n{'='*70}")
                print(f"🏭 SCRAPING {mfg_name.upper()} MACHINES")
                print(f"{'='*70}")
                
                cur.execute("""
                    SELECT DISTINCT machine_name 
                    FROM slot_machines 
                    WHERE manufacturer = %s
                    ORDER BY machine_name
                """, (mfg_name,))
                
                machines = [row[0] for row in cur.fetchall()]
                print(f"Found {len(machines)} {mfg_name} machines\n")
                
                success = 0
                for machine in machines:
                    spec = scraper_func(machine)
                    if spec and save_spec_to_db(spec):
                        success += 1
                    time.sleep(1.5)  # Polite delay
                
                total_success += success
                total_attempted += len(machines)
                
                if len(machines) > 0:
                    print(f"\n{mfg_name} Summary: {success}/{len(machines)} specs found ({success/len(machines)*100:.1f}%)")
    
    finally:
        conn.close()
    
    print(f"\n{'='*70}")
    print(f"📊 FINAL SUMMARY")
    print(f"{'='*70}")
    print(f"Total machines processed: {total_attempted}")
    print(f"Successful scrapes: {total_success}")
    if total_attempted > 0:
        print(f"Overall success rate: {total_success/total_attempted*100:.1f}%")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
