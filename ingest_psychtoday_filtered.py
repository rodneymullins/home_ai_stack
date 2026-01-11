import requests
from bs4 import BeautifulSoup
import psycopg2
import hashlib
import time

DB_CONFIG = {'database': 'research_papers', 'user': 'rod', 'host': '192.168.1.211'}
BASE_URL = "https://www.psychologytoday.com"
CONTRIBUTOR_URL = "https://www.psychologytoday.com/us/contributors/molly-s-castelloe-phd"

# Keywords to match (in URL or Title)
KEYWORDS = ['alienation', 'reunification', 'estrangement', 'parental', 'rights']

def get_filtered_articles():
    articles = []
    # Fetch deeper pages (try up to page 10 to find back catalog)
    max_pages = 10
    
    for page in range(1, max_pages + 1):
        url = f"{CONTRIBUTOR_URL}?page={page}"
        print(f"Scanning page {page}...")
        
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(url, headers=headers)
            if resp.status_code != 200:
                break
                
            soup = BeautifulSoup(resp.content, 'html.parser')
            page_found = 0
            
            for a in soup.find_all('a', href=True):
                href = a['href']
                text = a.get_text(strip=True)
                
                if '/us/blog/' in href and len(text) > 10:
                    full_url = href if href.startswith('http') else f"{BASE_URL}{href}"
                    
                    # Check relevancy strictly here
                    is_relevant = any(k in text.lower() or k in href.lower() for k in KEYWORDS)
                    
                    if is_relevant:
                        if not any(art['url'] == full_url for art in articles):
                            print(f"Found relevant: {text}")
                            articles.append({
                                'title': text,
                                'url': full_url,
                                'summary': "Relevant article found via crawl"
                            })
                            page_found += 1
            
            # Stop if page has no articles at all (end of list)
            # Actually, standard PT pages might just be empty or have "No posts found"
            if "No posts found" in soup.text:
                break
                
            if page_found == 0:
                 # If we found links but none relevant, we continue
                 # If we found NO blog links, we stop
                 blog_links = [a for a in soup.find_all('a', href=True) if '/us/blog/' in a['href']]
                 if not blog_links:
                     break
            
            time.sleep(1)
            
        except Exception as e:
            print(f"Error: {e}")
            break
            
    return articles

def ingest_articles(articles):
    if not articles:
        print("No relevant articles found.")
        return

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    count = 0
    for art in articles:
        try:
            pseudo_id = f"pt_{hashlib.md5(art['url'].encode()).hexdigest()[:12]}"
            
            # Check dupes
            cur.execute("SELECT id FROM papers WHERE source_url = %s", (art['url'],))
            if cur.fetchone():
                continue
                
            cur.execute("""
                INSERT INTO papers (
                    title, authors, source, source_url,
                    ssrn_id, journal, published_date,
                    abstract, quality_score, created_at, keywords
                ) VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, NOW(), %s
                )
            """, (
                art['title'],
                ["Molly S. Castelloe PhD"],
                'psychology_today',
                art['url'],
                pseudo_id,
                'Psychology Today',
                '2026-01-01',
                art['summary'],
                5.0,
                ["Parental Alienation"]
            ))
            count += 1
        except Exception as e:
            print(f"DB Error on {art['title']}: {e}")
            conn.rollback()
            continue
            
    conn.commit()
    print(f"Ingested {count} relevant articles.")
    cur.close()
    conn.close()

if __name__ == "__main__":
    arts = get_filtered_articles()
    ingest_articles(arts)
