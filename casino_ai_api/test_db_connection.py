#!/usr/bin/env python3
"""Test casino database connectivity"""
import sys
sys.path.insert(0, '/Users/rod/casino_ai_api')

from casino_data_fetcher import get_db_connection, fetch_slot_machines

try:
    print("🔍 Testing database connection...")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Test basic query
    cursor.execute("SELECT current_database(), current_user")
    db, user = cursor.fetchone()
    print(f"✅ Connected to database: {db} as user: {user}")
    
    # List tables
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE'
    """)
    tables = cursor.fetchall()
    print(f"\n📊 Found {len(tables)} tables:")
    for table in tables[:10]:
        print(f"  - {table[0]}")
    
    cursor.close()
    conn.close()
    
    # Test fetching slot machines
    print("\n🎰 Fetching slot machine data...")
    machines = fetch_slot_machines(limit=5)
    print(f"✅ Retrieved {len(machines)} machines")
    
    if machines:
        print("\nSample machine:")
        for key, value in list(machines[0].items())[:8]:
            print(f"  {key}: {value}")
    
    print("\n✅ All tests passed!")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
