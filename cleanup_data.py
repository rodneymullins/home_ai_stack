import psycopg2
import re
from config import DB_CONFIG

def normalize_title(title):
    """Normalize title for fuzzy duplicate detection."""
    if not title:
        return ""
    return re.sub(r'[^a-z0-9]', '', title.lower())

def cleanup_data():
    print("--- [CLEANUP] Starting Database Verification & Pruning ---")
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    try:
        # 1. Remove Records with Missing Authors
        # --------------------------------------
        print("\n--- Pruning Missing Metadata ---")
        cur.execute("""
            DELETE FROM papers 
            WHERE authors IS NULL 
               OR authors = '{}' 
               OR array_length(authors, 1) IS NULL
        """)
        deleted_metadata_count = cur.rowcount
        print(f"✅ Deleted {deleted_metadata_count} records with missing/empty authors.")

        # 2. Deduplication
        # ----------------
        print("\n--- Deduplicating Titles ---")
        cur.execute("SELECT id, title FROM papers ORDER BY id ASC")
        records = cur.fetchall()
        
        title_map = {}
        ids_to_delete = []
        
        for pid, title in records:
            norm = normalize_title(title)
            if norm in title_map:
                # We found a duplicate. Since we iterate by ID ASC, 
                # title_map[norm] is the "original" (oldest).
                # Current 'pid' is the newer duplicate to delete.
                ids_to_delete.append(pid)
                print(f"  - Marking duplicate ID {pid} (matches {title_map[norm]})")
            else:
                title_map[norm] = pid
                
        if ids_to_delete:
            cur.execute("DELETE FROM papers WHERE id = ANY(%s)", (ids_to_delete,))
            print(f"✅ Deleted {cur.rowcount} duplicate records.")
        else:
            print("✅ No duplicates found.")

        # Commit
        conn.commit()
        print("\n--- [CLEANUP] Success ---")
        
    except Exception as e:
        print(f"❌ [CLEANUP] Error: {e}")
        conn.rollback()
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    cleanup_data()
