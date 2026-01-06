import psycopg2

try:
    conn = psycopg2.connect(
        dbname="postgres",
        user="postgres",
        password="homeai2025",
        host="192.168.1.211",
        port="5432",
        connect_timeout=3
    )
    print("Success")
    conn.close()
except Exception as e:
    print(f"Failed: {e}")
