#!/usr/bin/env python3
"""
Analytics Engine - Advanced analytics computations for casino jackpot data
Provides ROI scoring, volatility analysis, pattern detection, and predictions
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import statistics
from utils.db_pool import get_db_connection

# Database configuration - matches google_trends_dashboard.py
DB_CONFIG = {'database': 'postgres', 'user': 'rod'}

def calculate_jvi(machine_name, days=30, mode='balanced'):
                MAX(hit_timestamp) as last_hit,
                EXTRACT(EPOCH FROM (NOW() - MAX(hit_timestamp)))/86400 as days_since_last
            FROM jackpots
            WHERE machine_name = %s
                AND hit_timestamp > NOW() - INTERVAL '%s days'
                AND amount IS NOT NULL
        """, (machine_name, days))
        
        result = cur.fetchone()
        cur.close()
        conn.close()
        
        if result and result['hit_count'] > 0:
            freq = result['hit_count']
            avg = result['avg_payout']
            max_payout = result['max_payout']
            days_since = result['days_since_last'] or 0
            
            # Recency factor: 1.0 if hit today, decays to 0.5 after 30 days
            recency = max(0.5, 1.0 - (days_since / 60))
            
            if mode == 'big':
                jvi = (freq * max_payout) / 10000
            elif mode == 'fast':
                jvi = (freq * freq * avg) / 100000
            else:  # balanced
                jvi = (freq * avg * recency) / 10000
            
            return {
                'machine_name': machine_name,
                'jvi': round(jvi, 2),
                'jvi_mode': mode,
                'hit_count': freq,
                'avg_payout': round(avg, 2),
                'max_payout': round(max_payout, 2),
                'days_since_last': round(days_since, 1)
            }
        
        return None
        
    except Exception as e:
        print(f"JVI calculation error: {e}")
        return None

def calculate_machine_roi(machine_name, days=30):
    """
    Calculate ROI score for a machine
    ROI = (hit_frequency * average_payout) / 1000
    Higher score = better player value
    """
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT 
                COUNT(*) as hit_count,
                AVG(amount) as avg_payout,
                MAX(amount) as max_payout,
                MIN(amount) as min_payout,
                MAX(location_id) as location_id
            FROM jackpots
            WHERE machine_name = %s
                AND hit_timestamp > NOW() - INTERVAL '%s days'
        """, (machine_name, days))
        
        result = cur.fetchone()
        cur.close()
        conn.close()
        
        if result and result['hit_count'] > 0:
            roi_score = (result['hit_count'] * result['avg_payout']) / 1000
            return {
                'machine_name': machine_name,
                'location_id': result.get('location_id', 'N/A'),
                'roi_score': round(roi_score, 2),
                'hit_count': result['hit_count'],
                'avg_payout': round(result['avg_payout'], 2),
                'max_payout': round(result['max_payout'], 2),
                'min_payout': round(result['min_payout'], 2)
            }
        
        return None
        
    except Exception as e:
        print(f"ROI calculation error: {e}")
        return None

def calculate_volatility(machine_name, days=30):
    """
    Calculate payout volatility (standard deviation)
    Higher volatility = more unpredictable payouts
    """
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        cur = conn.cursor()
        
        cur.execute("""
            SELECT amount
            FROM jackpots
            WHERE machine_name = %s
                AND amount IS NOT NULL
                AND hit_timestamp > NOW() - INTERVAL '%s days'
        """, (machine_name, days))
        
        amounts = [row[0] for row in cur.fetchall()]
        cur.close()
        conn.close()
        
        if len(amounts) >= 3:
            return {
                'machine_name': machine_name,
                'volatility': round(statistics.stdev(amounts), 2),
                'sample_size': len(amounts)
            }
        
        return None
        
    except Exception as e:
        print(f"Volatility calculation error: {e}")
        return None

def detect_hot_streaks(hours=24, min_hits=3):
    """
    Detect machines currently on hot streaks
    Returns machines with multiple hits in recent hours
    """
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT 
                machine_name,
                location_id,
                COUNT(*) as recent_hits,
                AVG(amount) as avg_payout,
                MAX(hit_timestamp) as last_hit,
                EXTRACT(EPOCH FROM (NOW() - MAX(hit_timestamp)))/3600 as hours_since_last
            FROM jackpots
            WHERE hit_timestamp > NOW() - INTERVAL '%s hours'
            GROUP BY machine_name, location_id
            HAVING COUNT(*) >= %s
            ORDER BY recent_hits DESC, last_hit DESC
            LIMIT 20
        """, (hours, min_hits))
        
        hot_machines = []
        for row in cur.fetchall():
            hot_machines.append({
                'machine_name': row['machine_name'],
                'location_id': row.get('location_id', 'N/A'),
                'recent_hits': row['recent_hits'],
                'avg_payout': round(row['avg_payout'], 2),
                'last_hit': row['last_hit'],
                'hours_since_last': round(row['hours_since_last'], 1),
                'heat_score': row['recent_hits'] * 10  # Simple heat metric
            })
        
        cur.close()
        conn.close()
        
        return hot_machines
        
    except Exception as e:
        print(f"Hot streak detection error: {e}")
        return []

def find_best_playing_times(machine_name=None):
    """
    Analyze best times to play based on historical jackpot frequency
    Returns hour-of-day analysis
    """
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        if machine_name:
            cur.execute("""
                SELECT 
                    hour_of_day,
                    COUNT(*) as hits,
                    AVG(amount) as avg_payout
                FROM jackpots
                WHERE machine_name = %s
                    AND hour_of_day IS NOT NULL
                GROUP BY hour_of_day
                ORDER BY hour_of_day
            """, (machine_name,))
        else:
            cur.execute("""
                SELECT 
                    hour_of_day,
                    COUNT(*) as hits,
                    AVG(amount) as avg_payout
                FROM jackpots
                WHERE hour_of_day IS NOT NULL
                GROUP BY hour_of_day
                ORDER BY hour_of_day
            """)
        
        results = []
        for row in cur.fetchall():
            # Convert 24h to 12h format
            hour = row['hour_of_day']
            period = 'AM' if hour < 12 else 'PM'
            display_hour = hour if hour <= 12 else hour - 12
            if display_hour == 0:
                display_hour = 12
            
            results.append({
                'hour': hour,
                'display': f"{display_hour}:00 {period}",
                'hits': row['hits'],
                'avg_payout': round(row['avg_payout'], 2)
            })
        
        cur.close()
        conn.close()
        
        return results
        
    except Exception as e:
        print(f"Best times analysis error: {e}")
        return []

def analyze_manufacturer_performance():
    """
    Compare performance across manufacturers
    """
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT 
                manufacturer,
                COUNT(*) as total_hits,
                SUM(amount) as total_payout,
                AVG(amount) as avg_payout,
                MAX(amount) as max_payout,
                COUNT(DISTINCT machine_name) as unique_machines
            FROM jackpots
            WHERE manufacturer IS NOT NULL
                AND manufacturer != 'Unknown'
            GROUP BY manufacturer
            ORDER BY total_hits DESC
        """)
        
        results = []
        for row in cur.fetchall():
            results.append({
                'manufacturer': row['manufacturer'],
                'total_hits': row['total_hits'],
                'total_payout': round(row['total_payout'], 2),
                'avg_payout': round(row['avg_payout'], 2),
                'max_payout': round(row['max_payout'], 2),
                'unique_machines': row['unique_machines'],
                'market_share': 0  # Will calculate after fetching all
            })
        
        # Calculate market share
        total_hits = sum(r['total_hits'] for r in results)
        for r in results:
            r['market_share'] = round((r['total_hits'] / total_hits) * 100, 1)
        
        cur.close()
        conn.close()
        
        return results
        
    except Exception as e:
        print(f"Manufacturer analysis error: {e}")
        return []

def get_game_family_insights():
    """
    Analyze performance by game family
    """
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT 
                game_family,
                COUNT(*) as hits,
                AVG(amount) as avg_payout,
                MAX(amount) as max_payout,
                COUNT(DISTINCT machine_name) as variants
            FROM jackpots
            WHERE game_family IS NOT NULL
                AND game_family != 'Unknown'
            GROUP BY game_family
            HAVING COUNT(*) >= 5
            ORDER BY hits DESC
            LIMIT 20
        """)
        
        results = []
        for row in cur.fetchall():
            results.append({
                'game_family': row['game_family'],
                'hits': row['hits'],
                'avg_payout': round(row['avg_payout'], 2),
                'max_payout': round(row['max_payout'], 2),
                'variants': row['variants']
            })
        
        cur.close()
        conn.close()
        
        return results
        
    except Exception as e:
        print(f"Game family analysis error: {e}")
        return []

def create_analytics_tables():
    """Create pre-computed analytics tables for performance"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        
        # Machine analytics summary table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS machine_analytics (
                machine_name TEXT PRIMARY KEY,
                total_hits INTEGER,
                total_payout DECIMAL(12,2),
                avg_payout DECIMAL(10,2),
                max_payout DECIMAL(10,2),
                roi_score DECIMAL(10,2),
                volatility_score DECIMAL(10,2),
                last_hit TIMESTAMP,
                hot_score INTEGER,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Hourly stats table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS hourly_stats (
                hour INTEGER,
                day_of_week INTEGER,
                total_hits INTEGER,
                avg_payout DECIMAL(10,2),
                PRIMARY KEY (hour, day_of_week)
            )
        """)
        
        conn.commit()
        cur.close()
        conn.close()
        
        print("✅ Analytics tables created")
        return True
        
    except Exception as e:
        print(f"❌ Analytics table creation failed: {e}")
        return False

def refresh_analytics_cache():
    """Refresh pre-computed analytics"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        
        # Refresh machine analytics
        cur.execute("""
            INSERT INTO machine_analytics (
                machine_name, total_hits, total_payout, avg_payout, 
                max_payout, last_hit, updated_at
            )
            SELECT 
                machine_name,
                COUNT(*) as total_hits,
                SUM(amount) as total_payout,
                AVG(amount) as avg_payout,
                MAX(amount) as max_payout,
                MAX(hit_timestamp) as last_hit,
                NOW() as updated_at
            FROM jackpots
            WHERE amount IS NOT NULL
            GROUP BY machine_name
            ON CONFLICT (machine_name) DO UPDATE SET
                total_hits = EXCLUDED.total_hits,
                total_payout = EXCLUDED.total_payout,
                avg_payout = EXCLUDED.avg_payout,
                max_payout = EXCLUDED.max_payout,
                last_hit = EXCLUDED.last_hit,
                updated_at = EXCLUDED.updated_at
        """)
        
        # Refresh hourly stats
        cur.execute("""
            INSERT INTO hourly_stats (hour, day_of_week, total_hits, avg_payout)
            SELECT 
                hour_of_day as hour,
                day_of_week,
                COUNT(*) as total_hits,
                AVG(amount) as avg_payout
            FROM jackpots
            WHERE hour_of_day IS NOT NULL 
                AND day_of_week IS NOT NULL
                AND amount IS NOT NULL
            GROUP BY hour_of_day, day_of_week
            ON CONFLICT (hour, day_of_week) DO UPDATE SET
                total_hits = EXCLUDED.total_hits,
                avg_payout = EXCLUDED.avg_payout
        """)
        
        conn.commit()
        cur.close()
        conn.close()
        
        print("✅ Analytics cache refreshed")
        return True
        
    except Exception as e:
        print(f"❌ Cache refresh failed: {e}")
        return False

if __name__ == '__main__':
    print("🎰 ANALYTICS ENGINE TEST\n")
    
    # Create tables
    print("Creating analytics tables...")
    create_analytics_tables()
    
    # Test hot streak detection
    print("\n🔥 Hot Machines (Last 24 hours):")
    hot = detect_hot_streaks(hours=24, min_hits=2)
    for m in hot[:5]:
        print(f"  {m['machine_name']}: {m['recent_hits']} hits, avg ${m['avg_payout']}")
    
    # Test manufacturer analysis
    print("\n🏭 Manufacturer Performance:")
    mfgs = analyze_manufacturer_performance()
    for m in mfgs:
        print(f"  {m['manufacturer']}: {m['total_hits']} hits ({m['market_share']}% share)")
    
    # Test game families
    print("\n🎮 Top Game Families:")
    families = get_game_family_insights()
    for f in families[:5]:
        print(f"  {f['game_family']}: {f['hits']} hits, avg ${f['avg_payout']}")
    
    print("\n✅ Analytics engine ready!")
