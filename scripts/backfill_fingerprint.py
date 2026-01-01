
import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
import hashlib
import sys
import os

# Add parent directory to path to find utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.db_pool import get_db_connection

def fingerprint_row(location_id, machine_name, hit_timestamp, amount, game_id, denomination):
    # Ensure None becomes '' to match the f-string logic
    # raw = f"{location_id}|{machine_name}|{hit_timestamp or ''}|{amount if amount is not None else ''}|{game_id or ''}|{denomination or ''}"
    
    # Precise recreation of the scraper's logic:
    ts_str = str(hit_timestamp) if hit_timestamp else ''
    amt_str = str(amount) if amount is not None else ''
    # Note: DB might return amount as Decimal, scraper uses float->str. 
    # But usually Decimal(1200.00) -> '1200.00'. float(1200.00) -> '1200.0'.
    # This is the tricky part. 
    # Let's trust that the scraper parses it as float and then hashes.
    # We should perform the same cast here.
    
    if amount is not None:
        try:
            amt_str = str(round(float(amount), 2))
        except:
            amt_str = str(amount)

    raw = f"{location_id}|{machine_name}|{ts_str}|{amt_str}|{game_id or ''}|{denomination or ''}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()

def backfill():
    print("🚀 Starting Fingerprint Backfill...")
    conn = get_db_connection()
    if not conn:
        print("❌ Failed to connect to DB")
        return

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # 1. Get all rows needing backfill
        print("Fetching rows without fingerprint...")
        cur.execute("SELECT id, location_id, machine_name, hit_timestamp, amount, game_id, denomination FROM jackpots WHERE fingerprint IS NULL")
        rows = cur.fetchall()
        print(f"Found {len(rows)} rows to update.")
        
        if not rows:
            return

        updates = []
        for row in rows:
            fp = fingerprint_row(
                row['location_id'], 
                row['machine_name'], 
                row['hit_timestamp'], 
                row['amount'], 
                row['game_id'], 
                row['denomination']
            )
            updates.append((fp, row['id']))
            
        print("Updating rows...")
        
        # Batch update
        execute_values(cur, 
            "UPDATE jackpots SET fingerprint = data.fp FROM (VALUES %s) AS data (fp, id) WHERE jackpots.id = data.id",
            updates,
            page_size=500
        )
        
        conn.commit()
        print(f"✅ Successfully backfilled {len(updates)} fingerprints.")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error during backfill: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    backfill()
