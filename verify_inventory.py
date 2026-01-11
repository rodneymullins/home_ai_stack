#!/usr/bin/env python3
"""
Verify slot_machines table population
"""
import psycopg2
from config import DB_CONFIG

try:
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    # Overall stats
    cur.execute("SELECT COUNT(*) FROM slot_machines")
    total = cur.fetchone()[0]
    print(f"✅ Total machines: {total:,}")
    
    # By manufacturer
    print("\n📊 By Manufacturer:")
    cur.execute("""
        SELECT manufacturer, COUNT(*) 
        FROM slot_machines 
        GROUP BY manufacturer 
        ORDER BY COUNT(*) DESC
    """)
    for manu, count in cur.fetchall():
        print(f"  {manu}: {count:,}")
    
    # By volatility
    print("\n🎲 By Volatility:")
    cur.execute("""
        SELECT volatility, COUNT(*) 
        FROM slot_machines 
        WHERE volatility IS NOT NULL
        GROUP BY volatility 
        ORDER BY COUNT(*) DESC
        LIMIT 5
    """)
    for vol, count in cur.fetchall():
        print(f"  {vol}: {count:,}")
    
    #Sample machines with metadata
    print("\n🎰 Sample Machines:")
    cur.execute("""
        SELECT machine_name, manufacturer, denomination, volatility
        FROM slot_machines
        WHERE volatility IS NOT NULL
        LIMIT 5
    """)
    for row in cur.fetchall():
        name, manu, denom, vol = row
        print(f"  {name} ({manu}, {denom}, {vol})")
    
    # Check JOIN with jackpots
    print("\n🔗 Cross-Reference with Jackpot Data:")
    cur.execute("""
        SELECT COUNT(DISTINCT j.machine_name)
        FROM jackpots j
        INNER JOIN slot_machines m ON j.machine_name = m.machine_name
    """)
    matched = cur.fetchone()[0]
    print(f"  Machines with jackpot history: {matched:,}")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
