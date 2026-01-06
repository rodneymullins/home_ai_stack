#!/usr/bin/env python3
"""
Browser-based manufacturer scraper using Playwright
Handles JavaScript-heavy sites that requests.get() can't reach
Requires: pip install playwright && playwright install chromium
"""
from playwright.sync_api import sync_playwright
import psycopg2
from datetime import datetime
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils.db_pool import get_db_connection
import re

def scrape_aristocrat_browser(machine_name, page):
    """Use browser to scrape Aristocrat's JavaScript site"""
    print(f"  Aristocrat (Browser): {machine_name[:30]}...", end=" ")
    
    search_term = machine_name.replace('(PROG)', '').replace('(MD)', '').strip()
    
    try:
        # Navigate to Aristocrat search
        page.goto(f"https://www.aristocratgaming.com/products", timeout=15000)
        
        # Wait for page to load
        page.wait_for_load_state('networkidle')
        
        # Type in search box
        search_input = page.locator('input[type="search"]').first
        if search_input.is_visible():
            search_input.fill(search_term)
            page.keyboard.press('Enter')
            page.wait_for_timeout(2000)
        
        # Extract game data
        content = page.content()
        
        data = {
            'machine_name': machine_name.upper(),
            'source': 'Aristocrat (Browser)',
            'url': page.url,
            'features': [],
            'rtp_percentage': None
        }
        
        # Look for RTP%
        rtp_match = re.search(r'RTP[:\s]+(\d+\.?\d*)%', content, re.IGNORECASE)
        if rtp_match:
            data['rtp_percentage'] = float(rtp_match.group(1))
        
        # Look for features
        feature_keywords = ['Free Games', 'Wild', 'Reel Power', 'Multiplier', 'Bonus']
        found = [f for f in feature_keywords if f.lower() in content.lower()]
        
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

def scrape_konami_browser(machine_name, page):
    """Konami with browser automation"""
    print(f"  Konami (Browser): {machine_name[:30]}...", end=" ")
    
    search_term = machine_name.replace('(PROG)', '').strip()
    
    try:
        page.goto("https://www.konamigaming.com/games", timeout=15000)
        page.wait_for_load_state('networkidle')
        
        # Find and use search
        search_box = page.locator('input[placeholder*="Search"]').first
        if search_box.is_visible():
            search_box.fill(search_term)
            page.wait_for_timeout(2000)
        
        content = page.content()
        
        data = {
            'machine_name': machine_name.upper(),
            'source': 'Konami (Browser)',
            'url': page.url,
            'features': []
        }
        
        features = ['Free Spins', 'Action Stacked', 'Balance of Fortune']
        found = [f for f in features if f.lower() in content.lower()]
        
        if found:
            data['features'] = found
            print(f"✓ ({len(found)} features)")
            return data
        
        print("✗")
        return None
        
    except Exception as e:
        print(f"✗ ({str(e)[:20]})")
        return None

def scrape_everi_browser(machine_name, page):
    """Everi browser scraping"""
    print(f"  Everi (Browser): {machine_name[:30]}...", end=" ")
    
    search_term = machine_name.replace('(PROG)', '').strip()
    
    try:
        page.goto("https://www.everi.com/games", timeout=15000)
        page.wait_for_load_state('networkidle')
        
        # Try search
        search = page.locator('input[type="search"], input[placeholder*="Search"]').first
        if search.is_visible():
            search.fill(search_term)
            page.wait_for_timeout(2000)
        
        content = page.content()
        
        data = {
            'machine_name': machine_name.upper(),
            'source': 'Everi (Browser)',
            'url': page.url,
            'features': []
        }
        
        features = ['Free Games', 'Wild', 'Multiplier', 'Progressive']
        found = [f for f in features if f.lower() in content.lower()]
        
        if found:
            data['features'] = found
            print(f"✓")
            return data
        
        print("✗")
        return None
        
    except Exception as e:
        print(f"✗ ({str(e)[:20]})")
        return None

def save_spec_to_db(spec):
    """Save to database"""
    try:
        conn = get_db_connection()
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
        return False

def main():
    """Run browser-based scraping for all manufacturers"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get machines from manufacturers that failed with requests
    cur.execute("""
        SELECT DISTINCT machine_name, manufacturer
        FROM slot_machines
        WHERE manufacturer IN ('Aristocrat', 'Konami', 'Everi')
            AND machine_name NOT ILIKE '%Poker%'
            AND machine_name NOT ILIKE '%Keno%'
        ORDER BY manufacturer, machine_name
        LIMIT 100
    """)
    
    machines = cur.fetchall()
    cur.close()
    conn.close()
    
    print(f"🌐 Browser-based scraping for {len(machines)} machines")
    print("⏳ Starting Playwright browser...\n")
    
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        page = context.new_page()
        
        scrapers = {
            'Aristocrat': scrape_aristocrat_browser,
            'Konami': scrape_konami_browser,
            'Everi': scrape_everi_browser
        }
        
        success_count = 0
        current_mfg = None
        
        for machine_name, manufacturer in machines:
            if manufacturer != current_mfg:
                current_mfg = manufacturer
                print(f"\n{'='*60}")
                print(f"🏭 {manufacturer.upper()}")
                print(f"{'='*60}\n")
            
            scraper = scrapers.get(manufacturer)
            if scraper:
                spec = scraper(machine_name, page)
                if spec and save_spec_to_db(spec):
                    success_count += 1
                time.sleep(2)  # Be polite
        
        browser.close()
    
    print(f"\n{'='*60}")
    print(f"✅ Browser scraping: {success_count}/{len(machines)} found ({success_count/len(machines)*100:.1f}%)")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
