
import psycopg2
import sys

hosts = [None, 'localhost', '127.0.0.1', '192.168.1.211']  # Thor's actual IP
user = 'rod'
dbname = 'postgres'

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
