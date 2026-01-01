
import psycopg2
import time

DB_CONFIG = {'database': 'postgres', 'user': 'rod'}

def get_db_connection():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"Error connecting to DB: {e}")
        return None

def fix_duplicates():
    print("🧹 Cleaning up duplicate jackpots...")
    conn = get_db_connection()
    if not conn:
        return
    
    cur = conn.cursor()
    
    try:
        # Check count before
        cur.execute("SELECT COUNT(*) FROM jackpots")
        count_before = cur.fetchone()[0]
        print(f"  Count before cleanup: {count_before}")
        
        # Delete duplicates (keep latest scraped_at, or just one of them)
        # Using ctid for consistent deletion of duplicates
        cur.execute("""
            DELETE FROM jackpots a USING jackpots b
            WHERE a.ctid < b.ctid
            AND a.location_id = b.location_id
            AND a.machine_name = b.machine_name
            AND a.hit_timestamp IS NOT DISTINCT FROM b.hit_timestamp
            AND a.amount IS NOT DISTINCT FROM b.amount
        """)
        deleted = cur.rowcount
        print(f"  Deleted {deleted} duplicate rows.")
        
        conn.commit()
        
        # Check count after
        cur.execute("SELECT COUNT(*) FROM jackpots")
        count_after = cur.fetchone()[0]
        print(f"  Count after cleanup: {count_after}")
        
        # Now try to force the unique constraint again
        print("🔒 Enforcing unique constraint...")
        try:
            cur.execute("ALTER TABLE jackpots DROP CONSTRAINT IF EXISTS unique_jackpot")
            conn.commit()
            cur.execute("ALTER TABLE jackpots ADD CONSTRAINT unique_jackpot UNIQUE (location_id, machine_name, hit_timestamp, amount)")
            conn.commit()
            print("  ✅ Constraint 'unique_jackpot' successfully applied!")
        except Exception as e:
            print(f"  ❌ Failed to apply constraint: {e}")
            
    except Exception as e:
        print(f"Error during cleanup: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    fix_duplicates()
