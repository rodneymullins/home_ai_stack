
import psycopg2
from datetime import datetime
from config import DB_CONFIG

try:
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    # Check Max Timestamp
    cur.execute("SELECT MAX(hit_timestamp) FROM jackpots")
    max_ts = cur.fetchone()[0]
    print(f"Max Hit Timestamp: {max_ts}")
    
    # Check Recent Inserts (by ID or approximate capability if no created_at? We don't have created_at)
    # But hit_timestamp is what matters for display.
    
    # Check count
    cur.execute("SELECT COUNT(*) FROM jackpots")
    count = cur.fetchone()[0]
    print(f"Total Rows: {count}")
    
    conn.close()
except Exception as e:
    print(e)
