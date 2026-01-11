import requests
from bs4 import BeautifulSoup
import psycopg2
import hashlib
import time

DB_CONFIG = {'database': 'research_papers', 'user': 'rod', 'host': '192.168.1.211'}
BASE_URL = "https://www.psychologytoday.com"
CONTRIBUTOR_URL = "https://www.psychologytoday.com/us/contributors/molly-s-castelloe-phd"

def get_articles():
    articles = []
    page = 1
    
    while True:
        url = f"{CONTRIBUTOR_URL}?page={page}" if page > 1 else CONTRIBUTOR_URL
        print(f"Fetching {url}...")
        
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(url, headers=headers)
            
            if resp.status_code != 200:
                print(f"Status {resp.status_code}. Stopping.")
                break
                
            soup = BeautifulSoup(resp.content, 'html.parser')
            
            # Find article links
            # Psychology Today listings usually look like:
            # <div class="profile-post-feed__item"> or similar
            # Let's look for standard links inside main content
            
            # Based on inspection, links might be just direct <a> tags with class or inside list items
            # Trying generic scraping for typical blog lists
            
            found_on_page = 0
            
            # Look for article listings
            # Common structure: <a href="..." class="profile-post-feed__title">
            for a in soup.find_all('a', href=True):
                href = a['href']
                text = a.get_text(strip=True)
                
                # Check if it looks like a blog article path: /us/blog/the-me-in-we/...
                if '/us/blog/' in href and len(text) > 10:
                    full_url = href if href.startswith('http') else f"{BASE_URL}{href}"
                    
                    # Deduplicate in list
                    if not any(art['url'] == full_url for art in articles):
                        # Attempt to find summary if it exists (often next sibling or close)
                        summary = ""
                        # Naive summary extraction: text of next sibling p or div
                        # This is 'best effort'
                        
                        articles.append({
                            'title': text,
                            'url': full_url,
                            'summary': summary
                        })
                        found_on_page += 1
            
            print(f"Found {found_on_page} articles on page {page}")
            
            if found_on_page == 0:
                break
                
            # Check for next page link
            next_link = soup.find('a', string=lambda t: t and 'Next' in t)
            if not next_link:
                break
                
            page += 1
            time.sleep(1)
            
        except Exception as e:
            print(f"Error fetching page {page}: {e}")
            break
            
    return articles

def ingest_articles(articles):
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    count = 0
    for art in articles:
        try:
            # Generate pseudo ID
            pseudo_id = f"pt_{hashlib.md5(art['url'].encode()).hexdigest()[:12]}"
            
            # Check dupes
            cur.execute("SELECT id FROM papers WHERE source_url = %s", (art['url'],))
            if cur.fetchone():
                continue
                
            cur.execute("""
                INSERT INTO papers (
                    title, authors, source, source_url,
                    ssrn_id, journal, published_date,
                    abstract, quality_score, created_at
                ) VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, NOW()
                )
            """, (
                art['title'],
                ["Molly S. Castelloe PhD"],
                'psychology_today',
                art['url'],
                pseudo_id,
                'Psychology Today',
                '2026-01-01', # Default date
                art['summary'] or "Psychology Today Article",
                5.0
            ))
            count += 1
        except Exception as e:
            print(f"DB Error on {art['title']}: {e}")
            conn.rollback()
            continue
            
    conn.commit()
    print(f"Ingested {count} articles.")
    cur.close()
    conn.close()

if __name__ == "__main__":
    articles = get_articles()
    print(f"Total articles found: {len(articles)}")
    ingest_articles(articles)
