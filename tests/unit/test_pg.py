import psycopg2
import sys
sys.path.insert(0, '..')
from config import DB_CONFIG

try:
    conn = psycopg2.connect(**DB_CONFIG, connect_timeout=3)
    print("Success")
    conn.close()
except Exception as e:
    print(f"Failed: {e}")
