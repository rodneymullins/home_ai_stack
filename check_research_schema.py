import psycopg2

DB_CONFIG = {'database': 'research_papers', 'user': 'rod', 'host': '192.168.1.211'}

def check_schema():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Check if 'papers' table exists and get columns
        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'papers';
        """)
        
        columns = cur.fetchall()
        if columns:
            print("Schema for 'papers' table:")
            for col in columns:
                print(f"- {col[0]}: {col[1]}")
        else:
            print("Table 'papers' not found in 'research_papers' database.")
            
            # List tables if papers not found
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public';
            """)
            tables = cur.fetchall()
            print("\nTables in public schema:")
            for t in tables:
                print(f"- {t[0]}")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_schema()
