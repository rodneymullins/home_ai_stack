import requests
from bs4 import BeautifulSoup
import re
import json

url = "https://www.coushattacasinoresort.com/gaming/slot-search/"
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

print("Fetching slot search page...")
r = requests.get(url, headers=headers, timeout=15)
soup = BeautifulSoup(r.text, 'html.parser')

# Extract all JavaScript
scripts = soup.find_all('script')
for script in scripts:
    if script.string and ('updateDiv' in script.string or 'slot' in script.string.lower()):
        content = script.string
        print("\n=== Relevant JavaScript ===")
        print(content[:1500])
        
        # Look for API endpoints or data URLs
        urls = re.findall(r'["\']([^"\']*(?:api|data|ajax|json)[^"\']*)["\']', content)
        if urls:
            print("\n=== Found potential API URLs ===")
            for u in urls:
                print(f"  {u}")
        
        # Look for JSON data
        json_matches = re.findall(r'\{[^{}]*\}', content)
        if json_matches:
            print(f"\n=== Found {len(json_matches)} JSON-like structures ===")
