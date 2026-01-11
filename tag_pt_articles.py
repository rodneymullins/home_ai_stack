import psycopg2

DB_CONFIG = {'database': 'research_papers', 'user': 'rod', 'host': '192.168.1.211'}

def tag_articles():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    # Tag specific known articles
    updates = [
        ("Signs of Parental Alienation", ["Parental Alienation", "Signs", "Psychology"]),
        ("Parental Alienation and Its Repair", ["Parental Alienation", "Reunification", "Therapy"])
    ]
    
    for title, tags in updates:
        print(f"Tagging {title}...")
        cur.execute("""
            UPDATE papers 
            SET keywords = %s, specific_topics = %s
            WHERE title = %s AND source = 'psychology_today'
        """, (tags, tags, title))
        
    conn.commit()
    cur.close()
    conn.close()
    print("Tags updated.")

if __name__ == "__main__":
    tag_articles()
