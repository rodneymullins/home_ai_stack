
import psycopg2
from config import DB_CONFIG

try:
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT denomination FROM jackpots ORDER BY denomination")
    print(cur.fetchall())
    conn.close()
except Exception as e:
    print(e)
