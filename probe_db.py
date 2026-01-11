
import psycopg2
import sys
from config import DB_CONFIG

# Probe multiple hosts - use config as primary
hosts = [DB_CONFIG.get('host'), None, 'localhost', '127.0.0.1']
user = DB_CONFIG.get('user', 'rod')
dbname = DB_CONFIG.get('database', 'postgres')

print("Probing DB connections...")

for host in hosts:
    print(f"Trying host={host} ...", end=" ")
    try:
        if host:
            conn = psycopg2.connect(database=dbname, user=user, host=host, connect_timeout=3)
        else:
            conn = psycopg2.connect(database=dbname, user=user, connect_timeout=3)
        print("SUCCESS!")
        conn.close()
        sys.exit(0)
    except Exception as e:
        print(f"FAILED: {e}")

sys.exit(1)
