import psycopg2

DB_CONFIG = {'database': 'research_papers', 'user': 'rod', 'host': '192.168.1.211'}

def find_urls():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    titles = [
        "Parental Alienation and Reunification Therapy: An Evidence-Based Review",
        "Evaluating Reunification Therapy from the Child's Perspective: Family Reunification and Restoration Program (FRRP)"
    ]
    
    print("--- Paper Locations ---")
    for t in titles:
        cur.execute("SELECT source_url, pdf_path FROM papers WHERE title = %s", (t,))
        res = cur.fetchone()
        if res:
            url, path = res
            print(f"Title: {t}")
            print(f"URL: {url}")
            if path:
                print(f"Local PDF: {path}")
            print("-" * 20)
        else:
            print(f"could not find: {t}")
            
    conn.close()

if __name__ == "__main__":
    find_urls()
