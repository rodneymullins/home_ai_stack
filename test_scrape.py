
import requests
from bs4 import BeautifulSoup
import time

url = "https://www.coushattacasinoresort.com/gaming/slot-search/"
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

print(f"Testing URL: {url}")
start = time.time()
try:
    r = requests.get(url, headers=headers, timeout=15)
    print(f"Status: {r.status_code}")
    print(f"Elapsed: {time.time() - start:.2f}s")
    print(f"Content Length: {len(r.text)}")
    soup = BeautifulSoup(r.text, 'html.parser')
    # Look for slot machine data - could be in tables, divs, or JSON
    tables = soup.find_all('table')
    print(f"Tables found: {len(tables)}")
    
    # Check for JavaScript data
    scripts = soup.find_all('script')
    for script in scripts:
        if script.string and 'slot' in script.string.lower():
            print(f"Script with 'slot': {script.string[:200]}...")
            break
    
    # Check for data rows
    rows = soup.find_all('tr')
    print(f"Table rows found: {len(rows)}")
    if rows:
        print(f"First row: {rows[0].get_text()[:100]}...")





except Exception as e:
    print(f"Error: {e}")
    print(f"Elapsed: {time.time() - start:.2f}s")
