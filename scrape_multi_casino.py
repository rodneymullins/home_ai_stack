#!/usr/bin/env python3
"""
Multi-Casino Jackpot Aggregator
Scrapes live jackpot data from casinos with online trackers
Similar to Coushatta's /slot-jackpot-updates page
"""
import requests
from bs4 import BeautifulSoup
import psycopg2
from datetime import datetime
import time

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
}

# Casinos with known jackpot trackers
# Casinos with known jackpot trackers
CASINOS = {
    'Coushatta': 'https://www.coushattacasinoresort.com/gaming/slot-jackpot-updates',
    'Choctaw Durant': 'https://www.choctawcasinos.com/durant/gaming/slot-jackpots',
    'WinStar': 'https://www.winstarworldcasino.com/gaming/slot-winners',
    'Hard Rock Tampa': 'https://www.seminolehardrocktampa.com/casino/slot-jackpots',
    'Seminole Hard Rock': 'https://www.seminolehardrockhollywood.com/casino/jackpots',
    'Pechanga': 'https://www.pechanga.com/gaming/slots/jackpots',
    'Mohegan Sun': 'https://mohegansun.com/gaming/slots/recent-jackpots',
    'Foxwoods': 'https://www.foxwoods.com/gaming/slots/jackpot-winners',
    # FireKeepers likely requires a specific dynamic page or social media scraping
    # 'FireKeepers': 'https://firekeeperscasino.com/gaming/slots/' 
}

def scrape_casino_jackpots(casino_name, base_url):
    """Generic jackpot scraper for casino websites"""
    print(f"\n🎰 Scraping {casino_name}...")
    print(f"URL: {base_url}")
    
    try:
        response = requests.get(base_url, headers=HEADERS, timeout=15)
        
        if response.status_code != 200:
            print(f"❌ HTTP {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        jackpots = []
        
        # Look for common jackpot table patterns
        # Pattern 1: Table with class containing 'jackpot' or 'winner'
        tables = soup.find_all('table', class_=lambda c: c and ('jackpot' in c.lower() or 'winner' in c.lower()))
        
        if not tables:
            # Pattern 2: Any table in main content
            tables = soup.find_all('table')
        
        if not tables:
            # Pattern 3: Div/list structure
            entries = soup.find_all('div', class_=lambda c: c and 'jackpot' in c.lower())
            if entries:
                print(f"Found {len(entries)} div-based jackpot entries")
                for entry in entries[:5]:  # Sample first 5
                    text = entry.get_text()
                    print(f"  Sample: {text[:100]}")
                return []
        
        # Parse table rows
        for table in tables:
            rows = table.find_all('tr')
            
            for row in rows[1:]:  # Skip header
                cols = row.find_all(['td', 'th'])
                if len(cols) >= 3:  # Machine, Amount, Date at minimum
                    
                    # Try to extract: machine name, amount, date
                    machine_name = cols[0].get_text(strip=True)
                    amount_text = None
                    date_text = None
                    
                    # Look for amount (contains $ or numeric)
                    for col in cols:
                        text = col.get_text(strip=True)
                        if '$' in text or (text.replace(',', '').replace('.', '').isdigit() and len(text) > 2):
                            amount_text = text
                        elif '/' in text or '-' in text:  # Date format
                            date_text = text
                    
                    if machine_name and amount_text:
                        # Clean amount
                        amount_cleaned = amount_text.replace('$', '').replace(',', '').strip()
                        try:
                            amount = float(amount_cleaned)
                            
                            jackpots.append({
                                'casino': casino_name,
                                'machine_name': machine_name.upper(),
                                'amount': amount,
                                'date_text': date_text,
                                'source_url': base_url
                            })
                        except ValueError:
                            continue
        
        print(f"✅ Found {len(jackpots)} jackpot records")
        return jackpots[:10]  # Return sample
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

def save_multi_casino_data(jackpots):
    """Save jackpot data with casino source"""
    try:
        conn = psycopg2.connect(database="postgres", user="rod")
        cur = conn.cursor()
        
        # Create multi-casino table if needed
        cur.execute("""
            CREATE TABLE IF NOT EXISTS multi_casino_jackpots (
                id SERIAL PRIMARY KEY,
                casino VARCHAR(100),
                machine_name VARCHAR(255),
                amount DECIMAL(10,2),
                date_text VARCHAR(100),
                source_url TEXT,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        inserted = 0
        for jp in jackpots:
            cur.execute("""
                INSERT INTO multi_casino_jackpots 
                (casino, machine_name, amount, date_text, source_url)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                jp['casino'],
                jp['machine_name'],
                jp['amount'],
                jp['date_text'],
                jp['source_url']
            ))
            inserted += 1
        
        conn.commit()
        cur.close()
        conn.close()
        
        print(f"💾 Saved {inserted} jackpots to database")
        return inserted
        
    except Exception as e:
        print(f"DB Error: {e}")
        return 0

def analyze_cross_casino_performance():
    """Compare machine performance across casinos"""
    try:
        conn = psycopg2.connect(database="postgres", user="rod")
        cur = conn.cursor()
        
        cur.execute("""
            SELECT machine_name, COUNT(DISTINCT casino) as casino_count, 
                   AVG(amount) as avg_payout, COUNT(*) as total_hits
            FROM multi_casino_jackpots
            GROUP BY machine_name
            HAVING COUNT(DISTINCT casino) > 1
            ORDER BY COUNT(DISTINCT casino) DESC, AVG(amount) DESC
            LIMIT 20
        """)
        
        results = cur.fetchall()
        
        print(f"\n📊 CROSS-CASINO MACHINE PERFORMANCE")
        print(f"{'='*70}")
        print(f"{'Machine':<40} {'Casinos':<10} {'Avg Payout':<15} {'Hits'}")
        print(f"{'='*70}")
        
        for machine, casinos, avg_payout, hits in results:
            print(f"{machine[:38]:<40} {casinos:<10} ${avg_payout:>10,.2f}   {hits}")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"Analysis error: {e}")

def main():
    """Scrape all casinos with online jackpot trackers"""
    print("🌐 MULTI-CASINO JACKPOT AGGREGATION")
    print(f"{'='*70}")
    print(f"Scanning {len(CASINOS)} casinos for jackpot data\n")
    
    all_jackpots = []
    successful_casinos = 0
    
    for casino_name, url in CASINOS.items():
        jackpots = scrape_casino_jackpots(casino_name, url)
        if jackpots:
            all_jackpots.extend(jackpots)
            successful_casinos += 1
        time.sleep(3)  # Be polite between casinos
    
    print(f"\n{'='*70}")
    print(f"📊 SUMMARY")
    print(f"{'='*70}")
    print(f"Casinos scraped: {successful_casinos}/{len(CASINOS)}")
    print(f"Total jackpots found: {len(all_jackpots)}")
    
    if all_jackpots:
        saved = save_multi_casino_data(all_jackpots)
        if saved:
            print("\n🔍 Running cross-casino analysis...")
            analyze_cross_casino_performance()

if __name__ == "__main__":
    main()
