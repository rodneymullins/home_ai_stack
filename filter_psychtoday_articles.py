import psycopg2

DB_CONFIG = {'database': 'research_papers', 'user': 'rod', 'host': '192.168.1.211'}

FILTER_KEYWORDS = ['alienation', 'reunification', 'estranged', 'estrangement']

def filter_articles():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    # Select all from this source
    cur.execute("SELECT id, title, abstract FROM papers WHERE source = 'psychology_today'")
    articles = cur.fetchall()
    
    deleted = 0
    kept = 0
    
    for aid, title, abstract in articles:
        text_content = f"{title.lower()} {abstract.lower()}"
        
        # Check if relevant
        is_relevant = any(kw in text_content for kw in FILTER_KEYWORDS)
        
        if not is_relevant:
            print(f"Removing irrelevant article: {title}")
            cur.execute("DELETE FROM papers WHERE id = %s", (aid,))
            deleted += 1
        else:
            print(f"Keeping valid article: {title}")
            kept += 1
            
    conn.commit()
    print(f"\nSummary: Kept {kept}, Removed {deleted}")
    cur.close()
    conn.close()

if __name__ == "__main__":
    filter_articles()
