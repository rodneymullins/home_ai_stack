import psycopg2
try:
    conn = psycopg2.connect(database='postgres', user='rod')
    print("Default connect success")
    conn.close()
except Exception as e:
    print(f"Default connect failed: {e}")

try:
    conn = psycopg2.connect(database='postgres', user='rod', host='localhost')
    print("Localhost connect success")
    conn.close()
except Exception as e:
    print(f"Localhost connect failed: {e}")
