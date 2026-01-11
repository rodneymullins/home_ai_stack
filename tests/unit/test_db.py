import psycopg2
import sys
sys.path.insert(0, '../..')
from config import DB_CONFIG

try:
    conn = psycopg2.connect(**DB_CONFIG)
    print("Config connect success")
    conn.close()
except Exception as e:
    print(f"Config connect failed: {e}")
