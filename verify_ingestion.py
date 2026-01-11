import psycopg2

DB_CONFIG = {'database': 'research_papers', 'user': 'rod', 'host': '192.168.1.211'}

def verify_counts():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        print("\n--- Paper Counts by Source ---")
        cur.execute("SELECT source, count(*) FROM papers GROUP BY source ORDER BY count(*) DESC")
        for source, count in cur.fetchall():
            print(f"{source}: {count}")
            
        print("\n--- Recent Additions (Last 10) ---")
        cur.execute("SELECT title, source, published_date FROM papers ORDER BY created_at DESC LIMIT 10")
        for t, s, d in cur.fetchall():
            print(f"[{s}] {t[:40]}... ({d})")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    verify_counts()
