"""Database helpers"""
import psycopg2
from psycopg2.extras import RealDictCursor

DB_CONFIG = {'database': 'postgres', 'user': 'rod'}

def get_conn():
    return psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)

def upsert_source(conn, casino: str, property_: str, base_url: str) -> int:
    with conn.cursor() as cur:
        cur.execute("""
          INSERT INTO sources (casino, property, base_url)
          VALUES (%s, %s, %s)
          ON CONFLICT (casino, property, base_url) DO UPDATE SET base_url = EXCLUDED.base_url
          RETURNING id
        """, (casino, property_, base_url))
        return cur.fetchone()['id']
