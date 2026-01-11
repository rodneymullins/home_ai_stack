import psycopg2

DB_CONFIG = {'database': 'research_papers', 'user': 'rod', 'host': '192.168.1.211'}

def analyze_db():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    # 1. Total Counts
    cur.execute("SELECT count(*) FROM papers")
    total = cur.fetchone()[0]
    
    cur.execute("SELECT source, count(*) FROM papers GROUP BY source ORDER BY count(*) DESC")
    sources = cur.fetchall()
    
    print(f"TOTAL PAPERS: {total}\n")
    print("BY SOURCE:")
    for s, c in sources:
        print(f"  - {s}: {c}")
        
    # 2. Most Relevant (Curated 'web_scrape' batch - Seminal & Recent)
    print("\n\n=== MOST RELEVANT: SEMINAL & RECENT (from Curated Research) ===")
    cur.execute("""
        SELECT title, authors, published_date, abstract 
        FROM papers 
        WHERE source = 'web_scrape' 
        ORDER BY published_date DESC
    """)
    curated = cur.fetchall()
    
    # Group by Era
    recent = []
    historical = []
    seminal = []
    
    for row in curated:
        title, authors, date, abstract = row
        year = date.year if date else 0
        fmt_auth = ", ".join(authors) if authors else "Unknown"
        item = f"* {title} ({year}) - {fmt_auth}"
        
        if year >= 2024:
            recent.append(item)
        elif year >= 2000:
            historical.append(item)
        else:
            seminal.append(item)
            
    print("\n--- 2024-2025 Cutting Edge ---")
    for i in recent: print(i)
    
    print("\n--- 2000-2023 Influential Era ---")
    for i in historical: print(i)
    
    print("\n--- Seminal Foundations ---")
    for i in seminal: print(i)
    
    # 3. High Value from Child Rights NGO (Dr. Authors)
    print("\n\n=== NOTABLE ARCHIVE: Child Rights NGO (Selected Dr. Authors) ===")
    cur.execute("""
        SELECT title, authors 
        FROM papers 
        WHERE source = 'child_rights_ngo' 
        AND (array_to_string(authors, ',') ILIKE '%Dr.%' OR title ILIKE '%Warshak%' OR title ILIKE '%Baker%')
        LIMIT 5
    """)
    crn_papers = cur.fetchall()
    for t, a in crn_papers:
        print(f"* {t} (Author: {a})")

    conn.close()

if __name__ == "__main__":
    analyze_db()
