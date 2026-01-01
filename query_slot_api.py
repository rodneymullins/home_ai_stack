import requests
from bs4 import BeautifulSoup

# Query the API endpoint with empty filters to get all slots
url = "https://www.coushattacasinoresort.com/ajax-slot-result-res.php?title=&denom=&manu=&type=&volatil="
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://www.coushattacasinoresort.com/gaming/slot-search/'
}

print("Querying slot inventory API...")
r = requests.get(url, headers=headers, timeout=15)

print(f"Status: {r.status_code}")
print(f"Content Length: {len(r.text)}")

# Parse the HTML response
soup = BeautifulSoup(r.text, 'html.parser')

# Look for slot entries - could be in divs, table rows, or list items
slots = []

# Try different selectors
rows = soup.find_all('tr')
divs = soup.find_all('div', class_=lambda x: x and 'slot' in x.lower())
items = soup.find_all(['li', 'article', 'section'])

print(f"\nFound {len(rows)} table rows")
print(f"Found {len(divs)} slot-related divs")
print(f"Found {len(items)} list items/sections")

# Extract first few entries as sample
if rows:
    print("\n=== Sample Table Rows ===")
    for i, row in enumerate(rows[:5]):
        print(f"{i+1}. {row.get_text(strip=True)[:150]}")
        
elif divs:
    print("\n=== Sample Divs ===")
    for i, div in enumerate(divs[:5]):
        print(f"{i+1}. {div.get_text(strip=True)[:150]}")
        
elif items:
    print("\n=== Sample Items ===")
    for i, item in enumerate(items[:5]):
        print(f"{i+1}. {item.get_text(strip=True)[:150]}")

# Print raw HTML sample if structured data not found
if not rows and not divs and not items:
    print("\n=== Raw HTML Sample ===")
    print(r.text[:1000])
