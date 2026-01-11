#!/usr/bin/env python3
"""
Casino Slot Floor Tracker
Monitors active machines, detects movements, and tracks floor changes
"""

import psycopg2
from datetime import datetime, timedelta
from typing import Dict, List

DB_CONFIG = {'database': 'postgres', 'user': 'rod', 'host': '192.168.1.211'}

def get_db():
    return psycopg2.connect(**DB_CONFIG)

def create_floor_history_table():
    """Create table to track floor snapshots"""
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS floor_snapshots (
            id SERIAL PRIMARY KEY,
            snapshot_date DATE NOT NULL,
            total_active_machines INT,
            total_locations INT,
            new_machines_week INT,
            removed_machines_month INT,
            turnover_rate DECIMAL(5,2),
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS machine_movements (
            id SERIAL PRIMARY KEY,
            location_id VARCHAR(50),
            machine_name VARCHAR(255),
            movement_type VARCHAR(20),  -- 'ADDED' or 'REMOVED'
            detected_date DATE,
            first_seen TIMESTAMP,
            last_seen TIMESTAMP,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    
    conn.commit()
    cur.close()
    conn.close()
    
    print("✅ Floor tracking tables created")

def get_active_machines(days=30):
    """Get list of active machines in last N days"""
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT DISTINCT location_id, machine_name
        FROM jackpots
        WHERE hit_timestamp > NOW() - INTERVAL '%s days'
    """, (days,))
    
    machines = {(row[0], row[1]) for row in cur.fetchall()}
    
    cur.close()
    conn.close()
    
    return machines

def detect_new_machines():
    """Find machines that appeared in last 7 days"""
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("""
        WITH this_week AS (
            SELECT DISTINCT location_id, machine_name,
                   MIN(hit_timestamp) as first_hit
            FROM jackpots
            WHERE hit_timestamp > NOW() - INTERVAL '7 days'
            GROUP BY location_id, machine_name
        ),
        before AS (
            SELECT DISTINCT location_id, machine_name
            FROM jackpots
            WHERE hit_timestamp < NOW() - INTERVAL '7 days'
        )
        SELECT t.location_id, t.machine_name, t.first_hit
        FROM this_week t
        LEFT JOIN before b ON t.location_id = b.location_id AND t.machine_name = b.machine_name
        WHERE b.machine_name IS NULL
    """)
    
    new_machines = []
    for row in cur.fetchall():
        new_machines.append({
            'location_id': row[0],
            'machine_name': row[1],
            'first_seen': row[2]
        })
    
    cur.close()
    conn.close()
    
    return new_machines

def detect_removed_machines():
    """Find machines that haven't hit in 60+ days but were active before"""
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("""
        WITH recent AS (
            SELECT DISTINCT location_id, machine_name
            FROM jackpots
            WHERE hit_timestamp > NOW() - INTERVAL '30 days'
        ),
        older AS (
            SELECT DISTINCT location_id, machine_name,
                   MAX(hit_timestamp) as last_hit
            FROM jackpots
            WHERE hit_timestamp BETWEEN NOW() - INTERVAL '90 days' AND NOW() - INTERVAL '60 days'
            GROUP BY location_id, machine_name
        )
        SELECT o.location_id, o.machine_name, o.last_hit
        FROM older o
        LEFT JOIN recent r ON o.location_id = r.location_id AND o.machine_name = r.machine_name
        WHERE r.machine_name IS NULL
    """)
    
    removed = []
    for row in cur.fetchall():
        removed.append({
            'location_id': row[0],
            'machine_name': row[1],
            'last_seen': row[2]
        })
    
    cur.close()
    conn.close()
    
    return removed

def calculate_floor_metrics():
    """Calculate current floor statistics"""
    conn = get_db()
    cur = conn.cursor()
    
    # Active machines (last 30 days)
    cur.execute("""
        SELECT COUNT(DISTINCT CONCAT(location_id, '|', machine_name))
        FROM jackpots
        WHERE hit_timestamp > NOW() - INTERVAL '30 days'
    """)
    active_machines = cur.fetchone()[0]
    
    # Total locations
    cur.execute("""
        SELECT COUNT(DISTINCT location_id)
        FROM jackpots
        WHERE hit_timestamp > NOW() - INTERVAL '30 days'
    """)
    total_locations = cur.fetchone()[0]
    
    # New this week
    new_machines = len(detect_new_machines())
    
    # Removed this month
    removed_machines = len(detect_removed_machines())
    
    # Turnover rate
    turnover_rate = (removed_machines / max(active_machines, 1)) * 100 if active_machines > 0 else 0
    
    cur.close()
    conn.close()
    
    return {
        'active_machines': active_machines,
        'total_locations': total_locations,
        'new_machines_week': new_machines,
        'removed_machines_month': removed_machines,
        'turnover_rate': round(turnover_rate, 2)
    }

def save_snapshot(metrics):
    """Save daily floor snapshot"""
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("""
        INSERT INTO floor_snapshots
        (snapshot_date, total_active_machines, total_locations, 
         new_machines_week, removed_machines_month, turnover_rate)
        VALUES (CURRENT_DATE, %s, %s, %s, %s, %s)
        ON CONFLICT DO NOTHING
    """, (
        metrics['active_machines'],
        metrics['total_locations'],
        metrics['new_machines_week'],
        metrics['removed_machines_month'],
        metrics['turnover_rate']
    ))
    
    conn.commit()
    cur.close()
    conn.close()

def save_movements(new_machines, removed_machines):
    """Record machine movements"""
    conn = get_db()
    cur = conn.cursor()
    
    for machine in new_machines:
        cur.execute("""
            INSERT INTO machine_movements
            (location_id, machine_name, movement_type, detected_date, first_seen)
            VALUES (%s, %s, 'ADDED', CURRENT_DATE, %s)
            ON CONFLICT DO NOTHING
        """, (machine['location_id'], machine['machine_name'], machine['first_seen']))
    
    for machine in removed_machines:
        cur.execute("""
            INSERT INTO machine_movements
            (location_id, machine_name, movement_type, detected_date, last_seen)
            VALUES (%s, %s, 'REMOVED', CURRENT_DATE, %s)
            ON CONFLICT DO NOTHING
        """, (machine['location_id'], machine['machine_name'], machine['last_seen']))
    
    conn.commit()
    cur.close()
    conn.close()

def get_hottest_locations(limit=10):
    """Get most active floor locations"""
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT location_id,
               COUNT(DISTINCT machine_name) as machine_count,
               COUNT(*) as jackpot_count
        FROM jackpots
        WHERE hit_timestamp > NOW() - INTERVAL '30 days'
        GROUP BY location_id
        ORDER BY jackpot_count DESC
        LIMIT %s
    """, (limit,))
    
    hottest = []
    for row in cur.fetchall():
        hottest.append({
            'location': row[0],
            'machines': row[1],
            'jackpots': row[2]
        })
    
    cur.close()
    conn.close()
    
    return hottest

def print_floor_report():
    """Print comprehensive floor report"""
    print("=" * 70)
    print("CASINO FLOOR STATUS REPORT")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    metrics = calculate_floor_metrics()
    
    print(f"\n📊 CURRENT FLOOR METRICS:")
    print(f"   Active Machines (30d): {metrics['active_machines']}")
    print(f"   Total Locations: {metrics['total_locations']}")
    print(f"   New This Week: {metrics['new_machines_week']}")
    print(f"   Removed This Month: {metrics['removed_machines_month']}")
    print(f"   Turnover Rate: {metrics['turnover_rate']}%")
    
    # New machines
    new = detect_new_machines()
    if new:
        print(f"\n🆕 RECENTLY ADDED ({len(new)}):")
        for m in new[:10]:
            print(f"   {m['location_id']}: {m['machine_name']}")
        if len(new) > 10:
            print(f"   ... and {len(new) - 10} more")
    
    # Removed machines
    removed = detect_removed_machines()
    if removed:
        print(f"\n❌ POSSIBLY REMOVED ({len(removed)}):")
        for m in removed[:10]:
            print(f"   {m['location_id']}: {m['machine_name']}")
        if len(removed) > 10:
            print(f"   ... and {len(removed) - 10} more")
    
    # Hottest locations
    hottest = get_hottest_locations(5)
    print(f"\n🔥 HOTTEST LOCATIONS:")
    for loc in hottest:
        print(f"   {loc['location']}: {loc['machines']} machines, {loc['jackpots']} jackpots")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    create_floor_history_table()
    
    # Generate and save metrics
    metrics = calculate_floor_metrics()
    save_snapshot(metrics)
    
    # Detect and save movements
    new_machines = detect_new_machines()
    removed_machines = detect_removed_machines()
    save_movements(new_machines, removed_machines)
    
    # Print report
    print_floor_report()
