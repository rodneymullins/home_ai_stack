#!/usr/bin/env python3
"""
Data Quality Verification Script
Checks completeness, accuracy, freshness, and consistency of casino data
"""
import sys
import os
# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db_pool import get_connection
from datetime import datetime, timedelta
import json

def check_completeness():
    """Verify all required fields are populated"""
    print("\n📋 COMPLETENESS CHECK")
    print("=" * 60)
    
    conn = get_connection()
    cur = conn.cursor()
    
    # Jackpots completeness
    cur.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(location_id) as has_location,
            COUNT(machine_name) as has_machine,
            COUNT(amount) as has_amount,
            COUNT(hit_timestamp) as has_timestamp
        FROM jackpots
    """)
    jp = cur.fetchone()
    
    print(f"Jackpots: {jp[0]:,} total")
    print(f"  Location ID:    {jp[1]:,} ({jp[1]/jp[0]*100:.1f}%)")
    print(f"  Machine Name:   {jp[2]:,} ({jp[2]/jp[0]*100:.1f}%)")
    print(f"  Amount:         {jp[3]:,} ({jp[3]/jp[0]*100:.1f}%)")
    print(f"  Timestamp:      {jp[4]:,} ({jp[4]/jp[0]*100:.1f}%)")
    
    # Slot machines completeness
    cur.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(manufacturer) as has_mfg,
            COUNT(denomination) as has_denom
        FROM slot_machines
    """)
    sm = cur.fetchone()
    
    print(f"\nSlot Machines: {sm[0]:,} total")
    print(f"  Manufacturer:   {sm[1]:,} ({sm[1]/sm[0]*100:.1f}%)")
    print(f"  Denomination:   {sm[2]:,} ({sm[2]/sm[0]*100:.1f}%)")
    
    cur.close()
    conn.close()
    
    return {
        'jackpots_complete': jp[1] == jp[0] and jp[2] == jp[0],
        'manufacturers_complete': sm[1] == sm[0]
    }

def check_accuracy():
    """Check for data anomalies and invalid values"""
    print("\n🎯 ACCURACY CHECK")
    print("=" * 60)
    
    conn = get_connection()
    cur = conn.cursor()
    
    # Check for unreasonably high/low jackpots
    cur.execute("""
        SELECT COUNT(*) FROM jackpots 
        WHERE amount < 10 OR amount > 1000000
    """)
    anomalies = cur.fetchone()[0]
    
    # Check for future timestamps
    cur.execute("""
        SELECT COUNT(*) FROM jackpots 
        WHERE hit_timestamp > NOW()
    """)
    future_timestamps = cur.fetchone()[0]
    
    # Check for very old timestamps (suspicious)
    cur.execute("""
        SELECT COUNT(*) FROM jackpots 
        WHERE hit_timestamp < NOW() - INTERVAL '2 years'
    """)
    old_timestamps = cur.fetchone()[0]
    
    print(f"Unusual amounts (< $10 or > $1M): {anomalies:,}")
    print(f"Future timestamps: {future_timestamps:,}")
    print(f"Very old timestamps (> 2 years): {old_timestamps:,}")
    
    cur.close()
    conn.close()
    
    return {
        'has_anomalies': anomalies > 0,
        'has_future_timestamps': future_timestamps > 0
    }

def check_freshness():
    """Verify data is being updated regularly"""
    print("\n⏰ FRESHNESS CHECK")
    print("=" * 60)
    
    conn = get_connection()
    cur = conn.cursor()
    
    # Most recent jackpot
    cur.execute("SELECT MAX(scraped_at) FROM jackpots")
    last_scrape = cur.fetchone()[0]
    
    # Most recent hit
    cur.execute("SELECT MAX(hit_timestamp) FROM jackpots")
    last_hit = cur.fetchone()[0]
    
    # Count from last 24 hours
    cur.execute("""
        SELECT COUNT(*) FROM jackpots 
        WHERE scraped_at > NOW() - INTERVAL '24 hours'
    """)
    recent_count = cur.fetchone()[0]
    
    print(f"Last scrape: {last_scrape}")
    print(f"Last jackpot hit: {last_hit}")
    print(f"Jackpots in last 24h: {recent_count:,}")
    
    if last_scrape:
        hours_since_scrape = (datetime.now() - last_scrape.replace(tzinfo=None)).total_seconds() / 3600
        print(f"Hours since last scrape: {hours_since_scrape:.1f}")
        
        is_fresh = hours_since_scrape < 24
        print(f"Status: {'✅ FRESH' if is_fresh else '⚠️ STALE'}")
    else:
        is_fresh = False
        print("Status: ❌ NO DATA")
    
    cur.close()
    conn.close()
    
    return {'is_fresh': is_fresh}

def check_consistency():
    """Check for duplicates and orphaned records"""
    print("\n🔗 CONSISTENCY CHECK")
    print("=" * 60)
    
    conn = get_connection()
    cur = conn.cursor()
    
    # Check for duplicate fingerprints (shouldn't happen with unique constraint)
    cur.execute("""
        SELECT fingerprint, COUNT(*) as cnt 
        FROM jackpots 
        GROUP BY fingerprint 
        HAVING COUNT(*) > 1
    """)
    duplicates = cur.fetchall()
    
    # Check for machines in jackpots but not in slot_machines
    cur.execute("""
        SELECT COUNT(DISTINCT j.machine_name) 
        FROM jackpots j
        LEFT JOIN slot_machines sm ON j.machine_name = sm.machine_name
        WHERE sm.machine_name IS NULL
    """)
    orphaned = cur.fetchone()[0]
    
    print(f"Duplicate fingerprints: {len(duplicates):,}")
    print(f"Machines in jackpots but not in slot_machines: {orphaned:,}")
    
    cur.close()
    conn.close()
    
    return {
        'has_duplicates': len(duplicates) > 0,
        'has_orphaned_machines': orphaned > 0
    }

def generate_report():
    """Run all checks and generate summary report"""
    print("\n" + "=" * 60)
    print("🔍 DATA QUALITY VERIFICATION REPORT")
    print("=" * 60)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        completeness = check_completeness()
        accuracy = check_accuracy()
        freshness = check_freshness()
        consistency = check_consistency()
        
        print("\n" + "=" * 60)
        print("📊 SUMMARY")
        print("=" * 60)
        
        all_checks = {
            'Jackpots Complete': completeness['jackpots_complete'],
            'Manufacturers Complete': completeness['manufacturers_complete'],
            'No Anomalies': not accuracy['has_anomalies'],
            'No Future Timestamps': not accuracy['has_future_timestamps'],
            'Data is Fresh': freshness['is_fresh'],
            'No Duplicates': not consistency['has_duplicates'],
            'No Orphaned Records': not consistency['has_orphaned_machines']
        }
        
        for check, passed in all_checks.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{check:.<40} {status}")
        
        overall_score = sum(all_checks.values()) / len(all_checks) * 100
        print(f"\nOverall Quality Score: {overall_score:.1f}%")
        
        if overall_score == 100:
            print("\n🎉 Excellent! All data quality checks passed!")
        elif overall_score >= 80:
            print("\n✅ Good data quality. Minor issues detected.")
        else:
            print("\n⚠️ Data quality needs attention.")
        
        print("\n" + "=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error during verification: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    generate_report()
