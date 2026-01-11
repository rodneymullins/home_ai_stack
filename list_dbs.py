import psycopg2

# Connect to 'postgres' db to list other dbs
DB_CONFIG = {'database': 'postgres', 'user': 'rod', 'host': '192.168.1.211'}

def list_dbs():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        cur.execute("SELECT datname FROM pg_database WHERE datistemplate = false;")
        
        dbs = cur.fetchall()
        print("Databases:")
        for db in dbs:
            print(f"- {db[0]}")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_dbs()
