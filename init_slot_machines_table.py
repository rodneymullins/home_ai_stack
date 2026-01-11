#!/usr/bin/env python3
"""
Initialize slot_machines table in PostgreSQL database
"""
import psycopg2
from config import DB_CONFIG

def create_slot_machines_table():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Drop existing table if needed (for clean re-creation)
        print("Creating slot_machines table...")
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS slot_machines (
                machine_name VARCHAR(255) PRIMARY KEY,
                manufacturer VARCHAR(100),
                denomination VARCHAR(20),
                type VARCHAR(50),
                volatility VARCHAR(50),
                location_code VARCHAR(20),
                photo_url TEXT,
                map_url TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes for performance
        print("Creating indexes...")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_manufacturer ON slot_machines(manufacturer)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_denomination ON slot_machines(denomination)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_volatility ON slot_machines(volatility)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_location ON slot_machines(location_code)")
        
        conn.commit()
        
        # Verify table creation
        cur.execute("SELECT COUNT(*) FROM slot_machines")
        count = cur.fetchone()[0]
        
        print(f"✅ Table created successfully!")
        print(f"Current record count: {count}")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise

if __name__ == "__main__":
    create_slot_machines_table()
