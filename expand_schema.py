#!/usr/bin/env python3
"""
Expand field lengths in slot_machines table
"""
import psycopg2
from config import DB_CONFIG


try:
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    print("Expanding field lengths...")
    
    # Increase type and volatility field lengths
    cur.execute("ALTER TABLE slot_machines ALTER COLUMN type TYPE VARCHAR(100)")
    cur.execute("ALTER TABLE slot_machines ALTER COLUMN volatility TYPE VARCHAR(100)")
    
    conn.commit()
    print("✅ Schema updated successfully!")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
