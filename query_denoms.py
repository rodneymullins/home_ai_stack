
import psycopg2
try:
    conn = psycopg2.connect(database="postgres", user="rod")
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT denomination FROM jackpots ORDER BY denomination")
    print(cur.fetchall())
    conn.close()
except Exception as e:
    print(e)
