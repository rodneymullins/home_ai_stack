import psycopg2

DB_CONFIG = {'database': 'wealth', 'user': 'rod', 'host': '192.168.1.211'}

def check_schema():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'papers';
        """)
        
        columns = cur.fetchall()
        print("Schema for 'papers' table:")
        for col in columns:
            print(f"- {col[0]}: {col[1]}")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_schema()
