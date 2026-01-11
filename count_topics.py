import psycopg2

DB_CONFIG = {'database': 'research_papers', 'user': 'rod', 'host': '192.168.1.211'}

def count_topics():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    # Define queries for specific topics
    queries = {
        "Parental Alienation": """
            SELECT count(*) FROM papers 
            WHERE title ILIKE '%parental alienation%' 
            OR abstract ILIKE '%parental alienation%'
            OR 'Parental Alienation' = ANY(keywords)
        """,
        "Reunification Therapy": """
            SELECT count(*) FROM papers 
            WHERE title ILIKE '%reunification%' 
            OR abstract ILIKE '%reunification%'
            OR 'Reunification Therapy' = ANY(keywords)
        """,
        "Both (Intersection)": """
            SELECT count(*) FROM papers 
            WHERE (title ILIKE '%parental alienation%' OR abstract ILIKE '%parental alienation%')
            AND (title ILIKE '%reunification%' OR abstract ILIKE '%reunification%')
        """
    }
    
    print("--- Paper Counts by Topic ---")
    for topic, sql in queries.items():
        cur.execute(sql)
        count = cur.fetchone()[0]
        print(f"{topic}: {count}")
        
    conn.close()

if __name__ == "__main__":
    count_topics()
