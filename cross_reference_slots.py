import requests
from bs4 import BeautifulSoup
import psycopg2

# Try querying with common manufacturers and aggregating results
manufacturers = ["IGT", "Aristocrat", "Konami", "Scientific Games", "AGS", "Everi", "Ainsworth"]
all_slots = {}

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://www.coushattacasinoresort.com/gaming/slot-search/'
}

print("Querying slot inventory by manufacturer...")
for manu in manufacturers:
    url = f"https://www.coushattacasinoresort.com/ajax-slot-result-res.php?title=&denom=&manu={manu}&type=&volatil="
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200 and len(r.text) > 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # Look for slot entries in various formats
            entries = soup.find_all(['tr', 'div', 'li'], class_=lambda x: x and ('slot' in str(x).lower() or 'game' in str(x).lower()))
            if not entries:
                entries = soup.find_all('tr')
            
            if entries:
                print(f"\n{manu}: Found {len(entries)} entries")
                for entry in entries[:3]:  # Sample first 3
                    text = entry.get_text(strip=True)[:100]
                    if text and text not in all_slots:
                        all_slots[text] = manu
                        print(f"  - {text}")
    except Exception as e:
        print(f"{manu}: Error - {e}")

print(f"\n\nTotal unique machines found: {len(all_slots)}")

# Now cross-reference with database
print("\n=== Cross-referencing with jackpot database ===")
try:
    conn = psycopg2.connect(database="postgres", user="rod")
    cur = conn.cursor()
    
    # Get distinct machines from jackpots
    cur.execute("SELECT DISTINCT machine_name FROM jackpots ORDER BY machine_name LIMIT 50")
    db_machines = [row[0] for row in cur.fetchall()]
    
    print(f"\nSample of {len(db_machines)} machines in database:")
    for m in db_machines[:10]:
        print(f"  - {m}")
    
    conn.close()
except Exception as e:
    print(f"DB Error: {e}")
