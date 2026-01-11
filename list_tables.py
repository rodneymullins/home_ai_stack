import psycopg2

DB_CONFIG = {'database': 'wealth', 'user': 'rod', 'host': '192.168.1.211'}

def list_tables():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_schema = 'public';
        """)
        
        tables = cur.fetchall()
        print("Tables in 'public' schema:")
        for t in tables:
            print(f"- {t[0]}.{t[1]}")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_tables()
