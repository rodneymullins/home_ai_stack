#!/usr/bin/env python3
"""
The Ultimate One Dashboard - Lord of the Rings Theme
Reorganized with embedded widgets and real-time data
"""

from flask import Flask, render_template_string, jsonify
from pytrends.request import TrendReq
import pandas as pd
from datetime import datetime
import random
import requests
import feedparser
from bs4 import BeautifulSoup
import psycopg2
from psycopg2.extras import RealDictCursor
import threading
import time
import sys
import os

# Import analytics engine
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from analytics_engine import (
        detect_hot_streaks, analyze_manufacturer_performance,
        get_game_family_insights, find_best_playing_times,
        calculate_machine_roi, calculate_volatility, calculate_jvi
    )
    ANALYTICS_AVAILABLE = True
except ImportError:
    ANALYTICS_AVAILABLE = False
    print("⚠️  Analytics engine not available")


app = Flask(__name__)

# Redis caching setup
try:
    from flask_caching import Cache
    cache = Cache(app, config={
        'CACHE_TYPE': 'redis',
        'CACHE_REDIS_URL': 'redis://localhost:6379/0',
        'CACHE_DEFAULT_TIMEOUT': 300
    })
    CACHE_AVAILABLE = True
except Exception as e:
    print(f"⚠️  Redis caching not available: {e}")
    CACHE_AVAILABLE = False
    # Dummy cache to prevent decorator errors
    class MockCache:
        def cached(self, timeout=300, **kwargs):
            def decorator(f):
                return f
            return decorator
        def memoize(self, timeout=300, **kwargs):
            def decorator(f):
                return f
            return decorator
    cache = MockCache()

# PostgreSQL connection for casino jackpots (Unix socket)
DB_CONFIG = {'database': 'postgres', 'user': 'rod'}

# Global cache for jackpots
jackpot_cache = []
jackpot_cache_time = None

SHARED_STYLES = """
    <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@400;700;900&family=Crimson+Text:wght@400;600&display=swap" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="/static/css/dashboard.css" rel="stylesheet">
"""

def get_db_connection():
    try:
        return psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        print(f"DB connection error: {e}")
        return None

def init_jackpot_table():
    try:
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS jackpots (
                    id SERIAL PRIMARY KEY,
                    location_id TEXT,
                    machine_name TEXT,
                    denomination TEXT,
                    amount DECIMAL(10,2),
                    game_id TEXT,
                    hit_timestamp TIMESTAMP,
                    page_num INTEGER,
                    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_scraped_at ON jackpots(scraped_at DESC)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_amount ON jackpots(amount DESC)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_machine_name ON jackpots(machine_name)")
            
            # Add columns if they don't exist
            try:
                cur.execute("ALTER TABLE jackpots ADD COLUMN IF NOT EXISTS amount DECIMAL(10,2)")
                cur.execute("ALTER TABLE jackpots ADD COLUMN IF NOT EXISTS game_id TEXT")
                cur.execute("ALTER TABLE jackpots ADD COLUMN IF NOT EXISTS hit_timestamp TIMESTAMP")
            except:
                pass
                
            # Add unique constraint to prevent duplicates
            try:
                cur.execute("ALTER TABLE jackpots ADD CONSTRAINT unique_jackpot UNIQUE (location_id, machine_name, hit_timestamp, amount)")
            except:
                pass
                
            conn.commit()
            cur.close()
            conn.close()
            print("✅ Jackpots table initialized")
    except Exception as e:
        print(f"Error initializing table: {e}")

def cleanup_jackpot_data():
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM jackpots WHERE machine_name ILIKE '%Poker%' OR machine_name ILIKE '%Keno%'")
            if cur.rowcount > 0:
                print(f"🧹 Purged {cur.rowcount} Poker/Keno entries from database")
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            print(f"Cleanup error: {e}")

# Scraping logic moved to standalone service: scrapers/coushatta_scraper.py
# Dashboard is now read-only - data populated by systemd service

def get_jackpots():
    global jackpot_cache, jackpot_cache_time
    if jackpot_cache and jackpot_cache_time:
        if (datetime.now() - jackpot_cache_time).seconds < 30:
            return jackpot_cache
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("SELECT location_id, machine_name, denomination, scraped_at, amount, hit_timestamp FROM jackpots WHERE machine_name NOT ILIKE '%Poker%' AND machine_name NOT ILIKE '%Keno%' ORDER BY hit_timestamp DESC NULLS LAST, scraped_at DESC LIMIT 50")
            jackpots = cur.fetchall()
            cur.close()
            conn.close()
            jackpot_cache = [dict(jp) for jp in jackpots]
            jackpot_cache_time = datetime.now()
            return jackpot_cache
        except Exception as e:
            print(f"Error fetching jackpots: {e}")
    return [{'location_id': 'HD0104', 'machine_name': 'IGT MULTI-GAME', 'denomination': '$1.00', 'scraped_at': datetime.now()}]

def get_hourly_analytics():
    """Get aggregate hit counts and averages by hour of day"""
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT 
                EXTRACT(HOUR FROM hit_timestamp) as hour,
                COUNT(*) as hits,
                ROUND(AVG(amount), 2) as avg_amount
            FROM jackpots
            GROUP BY 1
            ORDER BY 1
        """)
        return [dict(row) for row in cur.fetchall()]
    except Exception as e:
        print(f"Error fetching hourly analytics: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_jackpot_outliers(z_score_threshold=3, limit=10):
    """
    Find jackpots that are statistical outliers (>3 std devs from machine mean).
    Excluded machines with < 5 hits to ensure statistical relevance.
    """
    conn = get_db_connection()
    if not conn:
        return []

    try:
        # 1. Get stats per machine (mean, stddev)
        # 2. Join with jackpots to calculate Z-score
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            WITH machine_stats AS (
                SELECT 
                    machine_name,
                    AVG(amount) as mean,
                    STDDEV(amount) as stddev
                FROM jackpots 
                GROUP BY machine_name
                HAVING COUNT(*) > 5 AND STDDEV(amount) > 0
            )
            SELECT 
                j.machine_name,
                j.amount,
                j.hit_timestamp,
                j.location_id,
                j.denomination,
                ROUND((j.amount - s.mean) / s.stddev, 2) as z_score,
                ROUND(s.mean, 2) as avg_payout
            FROM jackpots j
            JOIN machine_stats s ON j.machine_name = s.machine_name
            WHERE (j.amount - s.mean) / s.stddev > %s
            ORDER BY z_score DESC
            LIMIT %s
        """, (z_score_threshold, limit))
        
        return [dict(row) for row in cur.fetchall()]
    except Exception as e:
        print(f"Error fetching outliers: {e}")
        return []
    finally:
        if conn:
            conn.close()

# Import stats service
from services.stats_service import get_jackpot_stats, classify_manufacturer

def get_bank_details(bank_id):
    conn = get_db_connection()
    if not conn: return None
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Bank Summary
        cur.execute("""
            SELECT 
                COUNT(*) as total_hits,
                ROUND(AVG(amount), 2) as avg_payout,
                MAX(amount) as max_payout,
                MIN(amount) as min_payout,
                MAX(hit_timestamp) as last_activity,
                COUNT(DISTINCT machine_name) as distinct_machines
            FROM jackpots
            WHERE location_id LIKE %s
        """, (f"{bank_id}%",))
        summary = dict(cur.fetchone() or {})
        summary['bank_id'] = bank_id
        
        # Machines in Bank
        cur.execute("""
            SELECT 
                machine_name,
                location_id,
                denomination,
                COUNT(*) as hits,
                ROUND(AVG(amount), 2) as avg_payout,
                MAX(amount) as max_payout,
                MAX(hit_timestamp) as last_hit
            FROM jackpots
            WHERE location_id LIKE %s
            GROUP BY machine_name, location_id, denomination
            ORDER BY hits DESC
        """, (f"{bank_id}%",))
        machines = [dict(row) for row in cur.fetchall()]
        
        # Recent Hits
        cur.execute("""
            SELECT machine_name, amount, hit_timestamp, denomination    
            FROM jackpots
            WHERE location_id LIKE %s
            ORDER BY hit_timestamp DESC
            LIMIT 20
        """, (f"{bank_id}%",))
        recent_hits = [dict(row) for row in cur.fetchall()]
        
        conn.close()
        return {'summary': summary, 'machines': machines, 'recent_hits': recent_hits}
    except Exception as e:
        print(f"Error details: {e}")
        if conn: conn.close()
        return None


def get_multi_casino_stats():
    """Get stats from multi_casino_jackpots table"""
    conn = get_db_connection()
    if not conn:
        return {}
        
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # 1. Latest Jackpots (Feed)
        try:
            cur.execute("""
                SELECT casino, machine_name, amount, date_text, source_url
                FROM multi_casino_jackpots
                ORDER BY id DESC
                LIMIT 50
            """)
            latest_jackpots = [dict(row) for row in cur.fetchall()]
        except:
            latest_jackpots = []

        # 2. Casino Leaderboard
        try:
            cur.execute("""
                SELECT casino, COUNT(*) as hits, AVG(amount) as avg_payout, MAX(amount) as max_payout
                FROM multi_casino_jackpots
                GROUP BY casino
                ORDER BY COUNT(*) DESC
            """)
            casinos = [dict(row) for row in cur.fetchall()]
        except:
            casinos = []
            
        # 3. Top Machines Aggregated
        try:
            cur.execute("""
                SELECT machine_name, COUNT(*) as hits, AVG(amount) as avg_payout, MAX(amount) as max_payout,
                       STRING_AGG(DISTINCT casino, ', ') as locations
                FROM multi_casino_jackpots
                GROUP BY machine_name
                HAVING COUNT(*) >= 2
                ORDER BY hits DESC, avg_payout DESC
                LIMIT 10
            """)
            top_machines = [dict(row) for row in cur.fetchall()]
        except:
            top_machines = []
        
        cur.close()
        conn.close()
        
        return {
            'latest': latest_jackpots,
            'casinos': casinos,
            'top_machines': top_machines
        }
        
    except Exception as e:
        print(f"Error multi-casino stats: {e}")
        return {}

def get_hourly_details():
    """Get full 24-hour jackpot statistics"""
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT 
                EXTRACT(HOUR FROM hit_timestamp) as hour,
                COUNT(*) as hit_count,
                ROUND(AVG(amount), 2) as avg_payout,
                MAX(amount) as max_payout,
                SUM(amount) as total_payout
            FROM jackpots
            WHERE hit_timestamp IS NOT NULL
            GROUP BY hour
            ORDER BY hour ASC
        """)
        rows = cur.fetchall()
        
        # Fill missing hours
        hourly_data = {int(row['hour']): row for row in rows}
        complete_data = []
        
        for h in range(24):
            time_label = f"{h-12} PM" if h > 12 else (f"{h} AM" if h > 0 else "12 AM")
            if h == 12: time_label = "12 PM"
            
            if h in hourly_data:
                row = hourly_data[h]
                complete_data.append({
                    'hour': h,
                    'label': time_label,
                    'hits': row['hit_count'],
                    'avg': float(row['avg_payout']),
                    'max': float(row['max_payout']),
                    'total': float(row['total_payout'])
                })
            else:
                complete_data.append({
                    'hour': h,
                    'label': time_label,
                    'hits': 0,
                    'avg': 0,
                    'max': 0,
                    'total': 0
                })
        
        return complete_data
    except Exception as e:
        print(f"Error getting hourly details: {e}")
        return []
    finally:
        cur.close()
        conn.close()


def get_all_machine_stats(sort_by='payout', limit=100):
    """Get stats for all machines for rankings (avg_payout or hits)"""
    conn = get_db_connection()
    if not conn:
        return []
        
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        order_clause = "avg_payout DESC"
        if sort_by == 'hits':
            order_clause = "hits DESC"
        elif sort_by == 'frequency':
            # Approximate frequency: hits / days since first hit (not perfect SQL sort, handled better in python or simple hits desc)
            order_clause = "hits DESC" 
            
        cur.execute(f"""
            SELECT 
                machine_name,
                location_id,
                COUNT(*) as hits,
                COUNT(*) FILTER (WHERE hit_timestamp > NOW() - INTERVAL '30 days') as hits_30d,
                ROUND(AVG(amount), 2) as avg_payout,
                MAX(amount) as max_payout,
                SUM(amount) as total_payout,
                MAX(hit_timestamp) as last_hit,
                MIN(hit_timestamp) as first_hit
            FROM jackpots
            WHERE amount IS NOT NULL AND machine_name NOT ILIKE '%Poker%' AND machine_name NOT ILIKE '%Keno%'
            GROUP BY machine_name, location_id
            HAVING COUNT(*) > 1
            ORDER BY {order_clause}
            LIMIT {limit}
        """)
        
        results = [dict(row) for row in cur.fetchall()]
        
        # Calculate trends and frequencies
        for m in results:
            days_active = (datetime.now() - m['first_hit']).days
            if days_active < 30: days_active = 30
            daily_avg = m['hits'] / days_active
            expected = daily_avg * 30
            ratio = m['hits_30d'] / expected if expected > 0 else 0
            
            if ratio > 1.2: m['color'] = '#ff6b6b' # Red (Heating Up)
            elif ratio < 0.6: m['color'] = '#4dabf7' # Blue (Slowing Down)
            else: m['color'] = '#ffffff' # White (Neutral)
            
            # Days per hit (using full active duration)
            m['days_per_hit'] = days_active / m['hits'] if m['hits'] > 0 else 0
                
        return results
    except Exception as e:
        print(f"Error getting ranking stats: {e}")
        return []
    finally:
        cur.close()
        conn.close()


def get_group_details(group_type, group_value):
    """Get stats for a specific group (zone, brand, denom)"""
    conn = get_db_connection()
    if not conn:
        return None
        
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        where_clause = ""
        params = [group_value]
        
        if group_type == 'zone':
            where_clause = "LEFT(location_id, 2) = %s"
        elif group_type == 'brand':
            if group_value == 'Top Dollar Family':
                where_clause = "machine_name ILIKE '%%Top Dollar%%'"
                params = []
            elif group_value == 'Huff N Puff':
                where_clause = "machine_name ILIKE '%%Huff%%Puff%%'"
                params = []
            else:
                where_clause = "machine_name ILIKE %s || '%%'"
        elif group_type == 'denom':
            where_clause = "denomination = %s"
            
        # Exclude Poker and Keno from all drilldown reports
        where_clause += " AND machine_name NOT ILIKE '%%Poker%%' AND machine_name NOT ILIKE '%%Keno%%'"
            
        # Overall Group Stats
        cur.execute(f"""
            SELECT 
                COUNT(*) as hits,
                ROUND(AVG(amount), 2) as avg_payout,
                MAX(amount) as max_payout,
                SUM(amount) as total_payout,
                MIN(hit_timestamp) as first_hit,
                MAX(hit_timestamp) as last_hit
            FROM jackpots
            WHERE {where_clause} AND amount IS NOT NULL
        """, params)
        stats = cur.fetchone()
        
        # Top Machines in Group
        cur.execute(f"""
            SELECT 
                machine_name,
                location_id,
                denomination,
                COUNT(*) as hits,
                ROUND(AVG(amount), 2) as avg_payout,
                MAX(amount) as max_payout
            FROM jackpots
            WHERE {where_clause} AND amount IS NOT NULL
            GROUP BY machine_name, location_id, denomination
            ORDER BY hits DESC
            LIMIT 50
        """, params)
        top_machines = [dict(row) for row in cur.fetchall()]
        
        # Recent Hits
        cur.execute(f"""
            SELECT *
            FROM jackpots
            WHERE {where_clause} AND amount IS NOT NULL
            ORDER BY hit_timestamp DESC
            LIMIT 20
        """, params)
        recent_hits = [dict(row) for row in cur.fetchall()]
        
        return {
            'stats': stats,
            'machines': top_machines,
            'recent': recent_hits,
            'type': group_type,
            'value': group_value
        }
    except Exception as e:
        print(f"Error getting group details: {e}")
        return None
    finally:
        cur.close()
        conn.close()

def get_machine_metadata(machine_name):
    """Get inventory metadata for a machine (manufacturer, volatility, photo, etc.)"""
    conn = get_db_connection()
    if not conn:
        return {}
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Try exact match first
        cur.execute("""
            SELECT manufacturer, denomination, type, volatility, location_code, photo_url, map_url
            FROM slot_machines
            WHERE machine_name = %s
        """, (machine_name,))
        row = cur.fetchone()
        
        # If no match, try fuzzy matching by stripping suffixes like (MD), (P), (PR)
        if not row:
            import re
            clean_name = re.sub(r'\s*\([^)]*\)\s*', ' ', machine_name).strip()
            cur.execute("""
                SELECT manufacturer, denomination, type, volatility, location_code, photo_url, map_url
                FROM slot_machines
                WHERE UPPER(machine_name) LIKE UPPER(%s)
                LIMIT 1
            """, (f"%{clean_name}%",))
            row = cur.fetchone()
        
        cur.close()
        conn.close()
        
        if row:
            # Clean volatility field (remove HTML artifacts)
            vol = row['volatility'] if row['volatility'] else 'Unknown'
            vol = vol.split('View')[0] if 'View' in vol else vol
            vol = vol.split('$')[0] if '$' in vol else vol
            
            return {
                'manufacturer': row['manufacturer'] or 'Unknown',
                'denomination': row['denomination'] or 'Unknown',
                'type': row['type'] or 'Unknown',
                'volatility': str(vol).strip(),
                'location_code': row['location_code'] or '',
                'photo_url': row['photo_url'] or '',
                'map_url': row['map_url'] or ''
            }
        return {
            'manufacturer': 'Unknown',
            'denomination': 'Unknown', 
            'type': 'Unknown',
            'volatility': 'Unknown',
            'location_code': '',
            'photo_url': '',
            'map_url': ''
        }
    except Exception as e:
        print(f"Error fetching metadata: {e}")
        return {
            'manufacturer': 'Unknown',
            'denomination': 'Unknown',
            'type': 'Unknown',
            'volatility': 'Unknown',
            'location_code': '',
            'photo_url': '',
            'map_url': ''
        }


def get_machine_details(machine_name):
    """Get detailed statistics for a specific machine using Pandas"""
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT hit_timestamp, amount, denomination, location_id
            FROM jackpots
            WHERE machine_name = %s
            ORDER BY hit_timestamp ASC
        """, (machine_name,))
        rows = cur.fetchall()
        
        if not rows:
            print(f"DEBUG: No jackpots found for machine: '{machine_name}'")
            print(f"DEBUG: Query was: SELECT * FROM jackpots WHERE machine_name = '{machine_name}'")
            return None
            
        # Pandas Analysis
        df = pd.DataFrame([dict(row) for row in rows])
        df['hit_timestamp'] = pd.to_datetime(df['hit_timestamp'])
        df['amount'] = pd.to_numeric(df['amount'])
        
        # Summary
        summary = {
            'machine_name': machine_name,
            'total_hits': len(df),
            'avg_payout': float(df['amount'].mean()),
            'max_payout': float(df['amount'].max()),
            'min_payout': float(df['amount'].min()),
            'total_paid': float(df['amount'].sum()),
            'payout_std': float(df['amount'].std() if len(df) > 1 else 0),
            'volatility': 'Unknown',
            'denomination': df['denomination'].iloc[0],
            'location_id': df['location_id'].iloc[0]
        }
        
        # Add inventory metadata
        metadata = get_machine_metadata(machine_name)
        
        # Update metadata carefully (only if valid)
        if metadata.get('manufacturer') and metadata['manufacturer'] != 'Unknown':
            summary['manufacturer'] = metadata['manufacturer']
        elif 'manufacturer' not in summary or summary['manufacturer'] == 'Unknown':
             # Try to classify if not found in metadata
             summary['manufacturer'] = classify_manufacturer(machine_name)
             
        if metadata.get('denomination') and metadata['denomination'] != 'Unknown':
             # If inventory has a specific denom, use it (or keep jackpot's if you prefer)
             # Usually jackpot denom is specific to the hit, inventory might be generic
             # Let's keep jackpot denom if we have it, otherwise use inventory
             if summary['denomination'] == 'Unknown' or not summary['denomination']:
                 summary['denomination'] = metadata['denomination']

        # Update other fields
        for key in ['type', 'volatility', 'location_code', 'photo_url', 'map_url']:
            if metadata.get(key) and metadata[key] != 'Unknown':
                summary[key] = metadata[key]
        
        # Pacing
        df['time_diff'] = df['hit_timestamp'].diff()
        avg_hours = df['time_diff'].mean().total_seconds() / 3600 if len(df) > 1 else 0
        pacing_str = f"{int(avg_hours)}h {int((avg_hours % 1) * 60)}m"
        
        # Heat Index (Rolling 7-day vs Average)
        last_7 = df[df['hit_timestamp'] > (datetime.now() - pd.Timedelta(days=7))]
        hits_7 = len(last_7)
        total_days = (df['hit_timestamp'].max() - df['hit_timestamp'].min()).days
        if total_days < 1: total_days = 1
        avg_weekly = (len(df) / total_days) * 7
        heat_score = (hits_7 / avg_weekly * 100) if avg_weekly > 0 else 0
        
        if heat_score > 150: heat_rating = "🔥 SUPER HOT"
        elif heat_score > 110: heat_rating = "Heating Up"
        elif heat_score > 90: heat_rating = "Normal"
        elif heat_score > 50: heat_rating = "Cooling Down"
        else: heat_rating = "🧊 ICE COLD"
        
        # Win Distribution
        bins = [0, 2000, 5000, 10000, float('inf')]
        labels = ['Small ($1.2k-$2k)', 'Medium ($2k-$5k)', 'High ($5k-$10k)', 'Grand ($10k+)']
        df['win_bucket'] = pd.cut(df['amount'], bins=bins, labels=labels)
        # Sort by range magnitude (index)
        counts = df['win_bucket'].value_counts().sort_index()
        dist = [{'label': k, 'count': v} for k,v in counts.items()]
        
        # Best Times
        df['hour'] = df['hit_timestamp'].dt.hour
        hourly = df.groupby('hour')['amount'].agg(['count', 'mean'])
        best_hours = []
        for h, row in hourly.nlargest(5, 'count').iterrows():
            time_str = f"{h-12} PM" if h > 12 else (f"{h} AM" if h > 0 else "12 AM")
            if h == 12: time_str = "12 PM"
            best_hours.append({'time': time_str, 'hits': int(row['count']), 'avg': float(row['mean'])})
            
        cv = summary['volatility'] / summary['avg_payout'] if summary['avg_payout'] > 0 and isinstance(summary['volatility'], (int, float)) else 0
        vol_rating = "High (Volatile)" if cv > 1.0 else ("Medium" if cv > 0.5 else "Low (Steady)")
        
        return {
            'summary': summary,
            'last_hit': {'hit_timestamp': df['hit_timestamp'].iloc[-1], 'amount': float(df['amount'].iloc[-1])},
            'best_hours': best_hours,
            'history': df.sort_values('hit_timestamp', ascending=False).head(20).to_dict('records'),
            'volatility_rating': vol_rating,
            'pacing': pacing_str,
            'heat_rating': heat_rating,
            'heat_score': int(heat_score),
            'distribution': dist
        }
    except Exception as e:
        print(f"Error getting details for '{machine_name}': {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        cur.close()
        conn.close()

def refresh_page_one():
    jackpots = scrape_jackpot_page(1)
    if not jackpots:
        return
    conn = get_db_connection()
    if not conn:
        return
    cur = conn.cursor()
    for jp in jackpots:
        try:
            # Check for duplicates manually to allow for missing unique constraints
            cur.execute("""
                SELECT 1 FROM jackpots 
                WHERE location_id = %s AND machine_name = %s AND amount = %s AND hit_timestamp = %s
            """, (jp['location_id'], jp['machine_name'], jp.get('amount'), jp.get('hit_timestamp')))
            
            if not cur.fetchone():
                cur.execute("""
                    INSERT INTO jackpots (location_id, machine_name, denomination, amount, game_id, hit_timestamp, page_num)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (jp['location_id'], jp['machine_name'], jp['denomination'], jp.get('amount'),
                      jp.get('game_id'), jp.get('hit_timestamp'), jp['page_num']))
        except Exception as e:
            print(f"Insert error: {e}")
            pass
    conn.commit()
    cur.close()
    conn.close()
    print("🔄 Refreshed page 1 jackpots")

# Background scraper removed - now handled by coushatta-scraper.timer systemd service


def format_time_ago(timestamp):
    if not timestamp:
        return "Recently"
    try:
        delta = datetime.now() - timestamp
        minutes = int(delta.total_seconds() / 60)
        if minutes < 1:
            return "Just now"
        elif minutes < 60:
            return f"{minutes}m ago"
        elif minutes < 1440:
            hours = minutes // 60
            return f"{hours}h ago"
        else:
            days = minutes // 1440
            return f"{days}d ago"
    except:
        return "Recently"

def get_trending_searches(geo='US'):
    # Region-specific demo data
    if geo == 'united_states':
        demo_data = [
            {'title': 'NFL Playoffs 2025', 'traffic': 'HOT'},
            {'title': 'Super Bowl Halftime Show', 'traffic': 'HOT'},
            {'title': 'New iPhone Release', 'traffic': 'HOT'},
            {'title': 'Tax Season 2025', 'traffic': 'HOT'},
            {'title': 'March Madness Bracket', 'traffic': 'HOT'}
        ]
    else:  # Global
        demo_data = [
            {'title': 'FIFA World Cup Qualifiers', 'traffic': 'HOT'},
            {'title': 'Climate Summit 2025', 'traffic': 'HOT'},
            {'title': 'SpaceX Mars Mission', 'traffic': 'HOT'},
            {'title': 'Olympics 2025', 'traffic': 'HOT'},
            {'title': 'Nobel Prize Winners', 'traffic': 'HOT'}
        ]
    
    try:
        pytrends = TrendReq(hl='en-US', tz=360, timeout=(10, 25), retries=2)
        trending = pytrends.trending_searches(pn=geo)
        result = [{'title': item, 'traffic': 'HOT'} for item in trending[0].head(5).tolist()]
        return result if result else demo_data
    except Exception as e:
        print(f"Using demo data for {geo}: {e}")
        return demo_data

def classify_manufacturer(machine_name):
    """Classify machine into manufacturer based on known game titles"""
    name = machine_name.lower()
    
    # Aristocrat
    if any(x in name for x in ['dragon link', 'dragon cash', 'lightning link', 'buffalo', 'dollar storm', 'wicked winnings', 'timber wolf', '5 dragons', 'walking dead', 'wild wild', 'game of thrones']):
        return 'Aristocrat'
        
    # Light & Wonder / SciGames / Bally
    if any(x in name for x in ['dancing drums', '88 fortunes', 'lock it link', 'ultimate fire link', 'jin ji bao xi', 'heidi', 'wizard of oz', 'monopoly', 'zeus', 'quick hit', 'invaders', 'huff']):
        return 'Light & Wonder'
        
    # IGT
    if any(x in name for x in ['wheel of fortune', 'double diamond', 'triple diamond', 'cleopatra', 'wolf run', 'da vinci diamonds', 'top dollar', 'megabucks', 'pinball', 'cats', 'golden goddess', 'sex and the city']):
        return 'IGT'
        
    # Konami
    if any(x in name for x in ['china shores', 'dragon\'s law', 'african diamond', 'lotus land', 'cobra hearts']):
        return 'Konami'
    
    return 'Other'

def get_news():
    try:
        feeds = [('https://www.cnbc.com/id/100003114/device/rss/rss.html', 'CNBC'), ('https://feeds.reuters.com/reuters/businessNews', 'Reuters')]
        news = []
        for feed_url, source in feeds:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:5]:
                    news.append({'title': entry.title, 'link': entry.link, 'source': source, 'published': entry.get('published', 'Recently')[:16]})
            except:
                pass
        return news[:10] if news else [{'title': 'Markets Rally on Strong Economic Data', 'link': '#', 'source': 'Demo News', 'published': 'Today'}]
    except Exception as e:
        print(f"Error fetching news: {e}")
        return [{'title': 'Markets Rally on Strong Economic Data', 'link': '#', 'source': 'Demo News', 'published': 'Today'}]

def get_services():
    return [
        {'name': 'Homer', 'icon': '🏠', 'url': 'http://192.168.1.176'},
        {'name': 'Jellyfin', 'icon': '🎬', 'url': 'http://192.168.1.176:8096'},
        {'name': 'Nextcloud', 'icon': '☁️', 'url': 'http://192.168.1.176:8083'},
        {'name': 'Jellyseerr', 'icon': '📺', 'url': 'http://192.168.1.176:5055'},
        {'name': 'Sonarr', 'icon': '📡', 'url': 'http://192.168.1.176:8989'},
        {'name': 'Radarr', 'icon': '🎥', 'url': 'http://192.168.1.176:7878'}
    ]

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>The One Dashboard • Middle-earth Finance</title>
    <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@400;700;900&family=Crimson+Text:wght@400;600&display=swap" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        :root { --gold: #d4af37; --bronze: #cd7f32; --dark-brown: #2c1810; --parchment: #f4e8d0; }
        body { font-family: 'Crimson Text', serif; background: linear-gradient(135deg, #1a0f0a 0%, #2c1810 50%, #1a0f0a 100%); color: var(--parchment); min-height: 100vh; position: relative; padding-bottom: 60px; }
        body::after { content: '💍'; position: fixed; font-size: 400px; top: 50%; left: 50%; transform: translate(-50%, -50%); opacity: 0.03; pointer-events: none; filter: blur(5px); }
        .container-fluid { padding: 20px; position: relative; z-index: 1; }
        header { text-align: center; margin-bottom: 20px; padding: 20px; background: linear-gradient(135deg, rgba(212, 175, 55, 0.1), rgba(205, 127, 50, 0.1)); border: 2px solid var(--gold); border-radius: 10px; box-shadow: 0 0 30px rgba(212, 175, 55, 0.3); }
        h1 { font-family: 'Cinzel', serif; font-size: 2.5em; font-weight: 900; color: var(--gold); text-shadow: 0 0 20px rgba(212, 175, 55, 0.8); letter-spacing: 4px; margin-bottom: 10px; }
        .subtitle { font-size: 1.1em; color: var(--bronze); font-style: italic; letter-spacing: 2px; }
        .nav-tabs { border-bottom: 2px solid var(--gold); margin-bottom: 20px; }
        .nav-tabs .nav-link { font-family: 'Cinzel', serif; color: var(--bronze); background: linear-gradient(135deg, rgba(44, 24, 16, 0.6), rgba(26, 15, 10, 0.6)); border: 2px solid var(--bronze); border-bottom: none; margin-right: 5px; padding: 10px 15px; font-weight: 700; letter-spacing: 1px; transition: all 0.3s; font-size: 0.85em; }
        .nav-tabs .nav-link:hover { background: linear-gradient(135deg, rgba(212, 175, 55, 0.2), rgba(205, 127, 50, 0.2)); color: var(--gold); border-color: var(--gold); }
        .nav-tabs .nav-link.active { background: linear-gradient(135deg, rgba(212, 175, 55, 0.3), rgba(205, 127, 50, 0.3)); color: var(--gold); border-color: var(--gold); box-shadow: 0 0 20px rgba(212, 175, 55, 0.5); }
        .scroll-card { background: linear-gradient(135deg, rgba(244, 232, 208, 0.15), rgba(212, 175, 55, 0.1)); backdrop-filter: blur(10px); border: 3px solid var(--gold); border-radius: 8px; padding: 20px; box-shadow: 0 8px 30px rgba(0, 0, 0, 0.5); margin-bottom: 20px; position: relative; }
        .scroll-card::before { content: '⚔'; position: absolute; top: 10px; left: 10px; font-size: 1.5em; color: var(--gold); opacity: 0.3; }
        .card-title { font-family: 'Cinzel', serif; font-size: 1.3em; font-weight: 700; color: var(--gold); margin-bottom: 15px; text-align: center; text-shadow: 0 0 10px rgba(212, 175, 55, 0.5); border-bottom: 2px solid var(--bronze); padding-bottom: 10px; }
        .chart-container { position: relative; height: 200px; margin-bottom: 15px; }
        .data-item { padding: 8px 12px; margin: 6px 0; background: linear-gradient(90deg, rgba(212, 175, 55, 0.1), rgba(205, 127, 50, 0.05)); border-left: 3px solid var(--gold); display: flex; align-items: center; gap: 12px; transition: all 0.3s; cursor: pointer; text-decoration: none; color: inherit; }
        .data-item:hover { background: linear-gradient(90deg, rgba(212, 175, 55, 0.3), rgba(205, 127, 50, 0.2)); transform: translateX(8px); box-shadow: 0 4px 15px rgba(212, 175, 55, 0.4); }
        .rank-badge { min-width: 30px; height: 30px; background: linear-gradient(135deg, var(--gold), var(--bronze)); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-family: 'Cinzel', serif; font-size: 0.9em; font-weight: 900; color: var(--dark-brown); box-shadow: 0 0 15px rgba(212, 175, 55, 0.6); }
        .trend-text { flex: 1; font-size: 0.95em; color: var(--parchment); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .news-item { padding: 15px; margin: 10px 0; background: linear-gradient(90deg, rgba(212, 175, 55, 0.08), rgba(205, 127, 50, 0.03)); border-left: 3px solid var(--gold); transition: all 0.3s; }
        .news-item:hover { background: linear-gradient(90deg, rgba(212, 175, 55, 0.15), rgba(205, 127, 50, 0.08)); transform: translateX(5px); }
        .news-title { font-size: 1.1em; font-weight: 600; color: var(--parchment); margin-bottom: 5px; }
        .news-source { font-size: 0.85em; color: var(--bronze); }
        .service-link { display: block; padding: 20px; margin: 10px 0; background: linear-gradient(135deg, rgba(212, 175, 55, 0.1), rgba(205, 127, 50, 0.05)); border: 2px solid var(--gold); border-radius: 8px; text-decoration: none; color: var(--parchment); text-align: center; transition: all 0.3s; }
        .service-link:hover { background: linear-gradient(135deg, rgba(212, 175, 55, 0.3), rgba(205, 127, 50, 0.2)); transform: translateY(-5px); box-shadow: 0 10px 30px rgba(212, 175, 55, 0.4); }
        .service-name { font-family: 'Cinzel', serif; font-size: 1.4em; font-weight: 700; color: var(--gold); margin-bottom: 5px; }
        .service-url { font-size: 0.9em; color: rgba(244, 232, 208, 0.7); }
        .jackpot-item { padding: 12px; margin: 8px 0; background: linear-gradient(90deg, rgba(212, 175, 55, 0.12), rgba(205, 127, 50, 0.06)); border-left: 4px solid var(--gold); border-radius: 4px; transition: all 0.3s; }
        .jackpot-item:hover { background: linear-gradient(90deg, rgba(212, 175, 55, 0.25), rgba(205, 127, 50, 0.15)); transform: translateX(5px); }
        .jackpot-machine { font-size: 1.05em; font-weight: 600; color: var(--parchment); margin-bottom: 5px; }
        .jackpot-details { font-size: 0.9em; color: rgba(244, 232, 208, 0.8); display: flex; gap: 15px; }
        .widget-container { background: rgba(244, 232, 208, 0.05); border: 2px solid var(--gold); border-radius: 8px; padding: 15px; margin-bottom: 20px; }
        .widget-container iframe { border: none; border-radius: 4px; }
        .footer { position: fixed; bottom: 0; left: 0; right: 0; height: 45px; background: linear-gradient(135deg, rgba(44, 24, 16, 0.95), rgba(26, 15, 10, 0.95)); backdrop-filter: blur(10px); border-top: 2px solid var(--gold); display: flex; align-items: center; justify-content: center; gap: 30px; font-family: 'Cinzel', serif; font-size: 0.85em; color: var(--gold); z-index: 100; }
    </style>
</head>
<body>
    <div class="container-fluid">
        <header>
            <h1>⚔ THE ONE DASHBOARD ⚔</h1>
            <div class="subtitle">Finance of Middle-earth</div>
        </header>
        
        <ul class="nav nav-tabs" role="tablist">
            <li class="nav-item"><button class="nav-link active" data-bs-toggle="tab" data-bs-target="#jackpots">🎰 Treasure Hunter</button></li>
            <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#links">🗺️ Paths</button></li>
            <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#trends">📜 Chronicles</button></li>
            <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#multicasino">🌍 World Watch</button></li>
            <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#analytics">📊 Analytics</button></li>
            <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#crypto">⛏️ Mithril</button></li>
            <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#treasury">💰 Treasures</button></li>
            <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#markets">🏛️ Markets</button></li>
            <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#news">📰 Tidings</button></li>
        </ul>
        
        <div class="tab-content">
            <!-- Multi-Casino Tab -->
            <div class="tab-pane fade" id="multicasino">
                <div class="row">
                    <div class="col-md-8">
                        <div class="scroll-card">
                            <h2 class="card-title">📡 Live Intelligence Feed</h2>
                            <div style="font-size: 0.8em; color: rgba(244, 232, 208, 0.6); margin-bottom: 15px;">Real-time intercepts from external casino networks</div>
                            {% if multi_casino and multi_casino.latest %}
                            {% for hit in multi_casino.latest %}
                            <div style="padding: 10px; margin: 5px 0; background: linear-gradient(90deg, rgba(32, 201, 151, 0.1), rgba(32, 201, 151, 0.02)); border-left: 3px solid #20c997; display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <div style="color: #20c997; font-weight: bold; font-size: 0.9em;">{{ hit.machine_name }}</div>
                                    <div style="font-size: 0.75em; color: rgba(244, 232, 208, 0.7);">{{ hit.casino }} • {{ hit.date_text }}</div>
                                </div>
                                <div style="text-align: right;">
                                    <div style="color: var(--gold); font-weight: bold; font-size: 1.1em;">${{ "{:,.2f}".format(hit.amount) }}</div>
                                    <a href="{{ hit.source_url }}" target="_blank" style="font-size: 0.7em; color: #aaa; text-decoration: none;">Source ↗</a>
                                </div>
                            </div>
                            {% endfor %}
                            {% else %}
                            <div style="text-align: center; color: #777; padding: 20px;">No incoming signals provided.</div>
                            {% endif %}
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="scroll-card">
                            <h2 class="card-title">🏆 Network Leaderboard</h2>
                            {% if multi_casino and multi_casino.casinos %}
                            {% for casino in multi_casino.casinos %}
                            <div style="padding: 10px; margin-bottom: 10px; border-bottom: 1px solid rgba(255,255,255,0.1);">
                                <div style="color: var(--gold); font-weight: bold;">{{ casino.casino }}</div>
                                <div style="display: flex; justify-content: space-between; font-size: 0.8em; margin-top: 5px;">
                                    <span>{{ casino.hits }} hits</span>
                                    <span style="color: #20c997;">Avg: ${{ "{:,.0f}".format(casino.avg_payout) }}</span>
                                </div>
                            </div>
                            {% endfor %}
                            {% endif %}
                            
                            <h3 class="card-title" style="margin-top: 30px; font-size: 1.1em;">🔥 Top Network Machines</h3>
                            {% if multi_casino and multi_casino.top_machines %}
                            {% for machine in multi_casino.top_machines %}
                            <div style="padding: 8px; margin: 4px 0; background: rgba(0,0,0,0.2);">
                                <div style="color: #fff; font-size: 0.9em;">{{ machine.machine_name }}</div>
                                <div style="font-size: 0.75em; color: #aaa;">Found at: {{ machine.locations }}</div>
                                <div style="display: flex; justify-content: space-between; font-size: 0.8em; margin-top: 2px;">
                                    <span style="color: var(--bronze);">{{ machine.hits }} hits</span>
                                    <span style="color: var(--gold);">${{ "{:,.0f}".format(machine.avg_payout) }}</span>
                                </div>
                            </div>
                            {% endfor %}
                            {% endif %}
                        </div>
                    </div>
                </div>
            </div>
            
            
            <!-- Analytics Tab -->
            <div class="tab-pane fade" id="analytics">
                <div class="scroll-card">
                    <h2 class="card-title">📊 Advanced Analytics Dashboard</h2>
                    <p style="text-align: center; color: rgba(244, 232, 208, 0.7); margin-bottom: 30px;">Deep insights into machine performance, player patterns, and market trends</p>
                    
                    <div class="row">
                        <div class="col-md-6 mb-3">
                            <a href="/transform-data" style="text-decoration: none; color: inherit;">
                                <div style="padding: 25px; background: linear-gradient(135deg, rgba(212, 175, 55, 0.15), rgba(205, 127, 50, 0.1)); border: 2px solid var(--gold); border-radius: 8px; transition: all 0.3s; cursor: pointer;">
                                    <div style="font-size: 2em; margin-bottom: 10px;">🔄</div>
                                    <h3 style="color: var(--gold); font-family: 'Cinzel', serif; margin-bottom: 10px;">Data Transformation</h3>
                                    <p style="color: rgba(244, 232, 208, 0.8); font-size: 0.9em;">Enrich existing data with manufacturer classification, game families, and time-based features</p>
                                </div>
                            </a>
                        </div>
                        
                        <div class="col-md-6 mb-3">
                            <a href="/analytics/machine-performance" style="text-decoration: none; color: inherit;">
                                <div style="padding: 25px; background: linear-gradient(135deg, rgba(32, 201, 151, 0.15), rgba(32, 201, 151, 0.1)); border: 2px solid #20c997; border-radius: 8px; transition: all 0.3s; cursor: pointer;">
                                    <div style="font-size: 2em; margin-bottom: 10px;">🎰</div>
                                    <h3 style="color: #20c997; font-family: 'Cinzel', serif; margin-bottom: 10px;">Machine Performance</h3>
                                    <p style="color: rgba(244, 232, 208, 0.8); font-size: 0.9em;">ROI scores, hot streaks, volatility analysis, and top performers</p>
                                </div>
                            </a>
                        </div>
                        
                        <div class="col-md-6 mb-3">
                            <a href="/analytics/player-patterns" style="text-decoration: none; color: inherit;">
                                <div style="padding: 25px; background: linear-gradient(135deg, rgba(255, 107, 107, 0.15), rgba(255, 107, 107, 0.1)); border: 2px solid #ff6b6b; border-radius: 8px; transition: all 0.3s; cursor: pointer;">
                                    <div style="font-size: 2em; margin-bottom: 10px;">📊</div>
                                    <h3 style="color: #ff6b6b; font-family: 'Cinzel', serif; margin-bottom: 10px;">Player Patterns</h3>
                                    <p style="color: rgba(244, 232, 208, 0.8); font-size: 0.9em;">Best playing times, weekend vs weekday analysis, temporal heatmaps</p>
                                </div>
                            </a>
                        </div>
                        
                        <div class="col-md-6 mb-3">
                            <a href="/analytics/manufacturer-wars" style="text-decoration: none; color: inherit;">
                                <div style="padding: 25px; background: linear-gradient(135deg, rgba(138, 43, 226, 0.15), rgba(138, 43, 226, 0.1)); border: 2px solid #8a2be2; border-radius: 8px; transition: all 0.3s; cursor: pointer;">
                                    <div style="font-size: 2em; margin-bottom: 10px;">⚔️</div>
                                    <h3 style="color: #8a2be2; font-family: 'Cinzel', serif; margin-bottom: 10px;">Manufacturer Wars</h3>
                                    <p style="color: rgba(244, 232, 208, 0.8); font-size: 0.9em;">Market share, performance comparison, manufacturer rankings</p>
                                </div>
                            </a>
                        </div>
                        
                        <div class="col-md-6 mb-3">
                            <a href="/analytics/game-families" style="text-decoration: none; color: inherit;">
                                <div style="padding: 25px; background: linear-gradient(135deg, rgba(255, 193, 7, 0.15), rgba(255, 193, 7, 0.1)); border: 2px solid #ffc107; border-radius: 8px; transition: all 0.3s; cursor: pointer;">
                                    <div style="font-size: 2em; margin-bottom: 10px;">🎮</div>
                                    <h3 style="color: #ffc107; font-family: 'Cinzel', serif; margin-bottom: 10px;">Game Families</h3>
                                    <p style="color: rgba(244, 232, 208, 0.8); font-size: 0.9em;">Series performance, game variants, cross-property analysis</p>
                                </div>
                            </a>
                        </div>
                        
                        <div class="col-md-6 mb-3">
                            <a href="/analytics/jvi-rankings" style="text-decoration: none; color: inherit;">
                                <div style="padding: 25px; background: linear-gradient(135deg, rgba(0, 255, 159, 0.15), rgba(0, 255, 159, 0.1)); border: 2px solid #00ff9f; border-radius: 8px; transition: all 0.3s; cursor: pointer;">
                                    <div style="font-size: 2em; margin-bottom: 10px;">💎</div>
                                    <h3 style="color: #00ff9f; font-family: 'Cinzel', serif; margin-bottom: 10px;">JVI Rankings</h3>
                                    <p style="color: rgba(244, 232, 208, 0.8); font-size: 0.9em;">Jackpot Value Index - balanced scoring, big payouts, fast hitters</p>
                                </div>
                            </a>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Trends Tab -->
            <div class="tab-pane fade" id="trends">
                <div class="row">
                    <div class="col-md-6">
                        <div class="scroll-card">
                            <h2 class="card-title">🏔 Trending in the West</h2>
                            <div class="chart-container"><canvas id="usChart"></canvas></div>
                            {% for item in trending_us %}
                            <a href="https://www.google.com/search?q={{ item.title | urlencode }}" target="_blank" class="data-item">
                                <div class="rank-badge">{{ loop.index }}</div>
                                <div class="trend-text">{{ item.title }}</div>
                            </a>
                            {% endfor %}
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="scroll-card">
                            <h2 class="card-title">🌍 Across All Realms</h2>
                            <div class="chart-container"><canvas id="globalChart"></canvas></div>
                            {% for item in trending_global %}
                            <a href="https://www.google.com/search?q={{ item.title | urlencode }}" target="_blank" class="data-item">
                                <div class="rank-badge">{{ loop.index }}</div>
                                <div class="trend-text">{{ item.title }}</div>
                            </a>
                            {% endfor %}
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Mithril Tab (Crypto) -->
            <div class="tab-pane fade" id="crypto">
                <div class="scroll-card">
                    <h2 class="card-title">⛏️ Mithril: Bitcoin & Cryptocurrency</h2>
                    <div class="widget-container">
                        <!-- TradingView Widget BEGIN -->
                        <div class="tradingview-widget-container">
                          <div class="tradingview-widget-container__widget"></div>
                          <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-symbol-overview.js" async>
                          {
                          "symbols": [
                            ["COINBASE:BTCUSD|1D"],
                            ["COINBASE:ETHUSD|1D"],
                            ["COINBASE:SOLUSD|1D"],
                            ["COINBASE:ADAUSD|1D"]
                          ],
                          "chartOnly": false,
                          "width": "100%",
                          "height": "600",
                          "locale": "en",
                          "colorTheme": "dark",
                          "autosize": true,
                          "showVolume": false,
                          "showMA": false,
                          "hideDateRanges": false,
                          "hideMarketStatus": false,
                          "hideSymbolLogo": false,
                          "scalePosition": "right",
                          "scaleMode": "Normal",
                          "fontFamily": "-apple-system, BlinkMacSystemFont, Trebuchet MS, Roboto, Ubuntu, sans-serif",
                          "fontSize": "10",
                          "noTimeScale": false,
                          "valuesTracking": "1",
                          "changeMode": "price-and-percent",
                          "chartType": "area",
                          "maLineColor": "#2962FF",
                          "maLineWidth": 1,
                          "maLength": 9,
                          "backgroundColor": "rgba(19, 23, 34, 0)",
                          "lineWidth": 2,
                          "lineType": 0,
                          "dateRanges": [
                            "1d|1",
                            "1m|30",
                            "3m|60",
                            "12m|1D",
                            "60m|1W",
                            "all|1M"
                          ]
                          }
                          </script>
                        </div>
                        <!-- TradingView Widget END -->
                    </div>
                </div>
            </div>
            
            <!-- Treasures Tab (Fed Treasury) -->
            <div class="tab-pane fade" id="treasury">
                <div class="scroll-card">
                    <h2 class="card-title">💰 Treasures: Fed Treasury Data</h2>
                    <div class="widget-container">
                        <!-- TradingView Widget BEGIN -->
                        <div class="tradingview-widget-container">
                          <div class="tradingview-widget-container__widget"></div>
                          <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-market-quotes.js" async>
                          {
                          "width": "100%",
                          "height": "600",
                          "symbolsGroups": [
                            {
                              "name": "Treasury Bills",
                              "symbols": [
                                {"name": "TVC:US01MY", "displayName": "1 Month"},
                                {"name": "TVC:US03MY", "displayName": "3 Month"},
                                {"name": "TVC:US06MY", "displayName": "6 Month"},
                                {"name": "TVC:US01Y", "displayName": "1 Year"}
                              ]
                            },
                            {
                              "name": "Treasury Notes",
                              "symbols": [
                                {"name": "TVC:US02Y", "displayName": "2 Year"},
                                {"name": "TVC:US05Y", "displayName": "5 Year"},
                                {"name": "TVC:US10Y", "displayName": "10 Year"}
                              ]
                            },
                            {
                              "name": "Treasury Bonds",
                              "symbols": [
                                {"name": "TVC:US20Y", "displayName": "20 Year"},
                                {"name": "TVC:US30Y", "displayName": "30 Year"}
                              ]
                            }
                          ],
                          "showSymbolLogo": true,
                          "isTransparent": true,
                          "colorTheme": "dark",
                          "locale": "en",
                          "backgroundColor": "rgba(19, 23, 34, 0)"
                          }
                          </script>
                        </div>
                        <!-- TradingView Widget END -->
                    </div>
                </div>
            </div>
            
            <!-- Markets Tab (Stocks & Economic Indicators) -->
            <div class="tab-pane fade" id="markets">
                <div class="scroll-card">
                    <h2 class="card-title">🏛️ Markets: NASDAQ & Economic Indicators</h2>
                    <div class="widget-container">
                        <!-- TradingView Widget BEGIN -->
                        <div class="tradingview-widget-container">
                          <div class="tradingview-widget-container__widget"></div>
                          <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-market-overview.js" async>
                          {
                          "colorTheme": "dark",
                          "dateRange": "12M",
                          "showChart": true,
                          "locale": "en",
                          "width": "100%",
                          "height": "600",
                          "largeChartUrl": "",
                          "isTransparent": true,
                          "showSymbolLogo": true,
                          "showFloatingTooltip": false,
                          "plotLineColorGrowing": "rgba(41, 98, 255, 1)",
                          "plotLineColorFalling": "rgba(41, 98, 255, 1)",
                          "gridLineColor": "rgba(240, 243, 250, 0)",
                          "scaleFontColor": "rgba(106, 109, 120, 1)",
                          "belowLineFillColorGrowing": "rgba(41, 98, 255, 0.12)",
                          "belowLineFillColorFalling": "rgba(41, 98, 255, 0.12)",
                          "belowLineFillColorGrowingBottom": "rgba(41, 98, 255, 0)",
                          "belowLineFillColorFallingBottom": "rgba(41, 98, 255, 0)",
                          "symbolActiveColor": "rgba(41, 98, 255, 0.12)",
                          "tabs": [
                            {
                              "title": "Indices",
                              "symbols": [
                                {"s": "NASDAQ:NDX", "d": "NASDAQ 100"},
                                {"s": "SP:SPX", "d": "S&P 500"},
                                {"s": "DJIA:DJI", "d": "Dow Jones"}
                              ],
                              "originalTitle": "Indices"
                            },
                            {
                              "title": "Economic",
                              "symbols": [
                                {"s": "ECONOMICS:USIRYY", "d": "Inflation Rate"},
                                {"s": "ECONOMICS:USUNR", "d": "Unemployment"},
                                {"s": "ECONOMICS:USGDPQQ", "d": "GDP Growth"},
                                {"s": "FRED:FEDFUNDS", "d": "Fed Funds Rate"}
                              ],
                              "originalTitle": "Economic"
                            }
                          ]
                          }
                          </script>
                        </div>
                        <!-- TradingView Widget END -->
                    </div>
                </div>
            </div>
            
            <!-- News Tab -->
            <div class="tab-pane fade" id="news">
                <div class="scroll-card">
                    <h2 class="card-title">📰 Tidings from Afar</h2>
                    {% for article in news_data %}
                    <a href="{{ article.link }}" target="_blank" class="news-item" style="display: block; text-decoration: none; color: inherit;">
                        <div class="news-title">{{ article.title }}</div>
                        <div class="news-source">{{ article.source }} • {{ article.published }}</div>
                    </a>
                    {% endfor %}
                </div>
            </div>
            
            <!-- Links Tab -->
            <div class="tab-pane fade" id="links">
                <div class="row">
                    {% for service in services %}
                    <div class="col-md-6 col-lg-4">
                        <a href="{{ service.url }}" target="_blank" class="service-link">
                            <div class="service-name">{{ service.icon }} {{ service.name }}</div>
                            <div class="service-url">{{ service.url }}</div>
                        </a>
                    </div>
                    {% endfor %}
                </div>
            </div>
            
            <!-- Casino Jackpots Tab -->
            <div class="tab-pane fade show active" id="jackpots">
                <div class="row">
                    <!-- Column 1: Essentials -->
                    <div class="col-md-4">
                        <div class="scroll-card">
                            <h2 class="card-title">📊 Casino Analytics</h2>
                            
                            <!-- Overall Stats -->
                            <div style="background: linear-gradient(135deg, rgba(212, 175, 55, 0.15), rgba(205, 127, 50, 0.1)); padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; text-align: center;">
                                    <div>
                                        <div style="font-size: 1.8em; color: var(--gold); font-family: 'Cinzel', serif;">${{ "{:,.2f}".format(stats.avg_jackpot) }}</div>
                                        <div style="font-size: 0.8em; color: rgba(244, 232, 208, 0.7);">Avg Jackpot</div>
                                    </div>
                                    <div>
                                        <div style="font-size: 1.8em; color: var(--bronze); font-family: 'Cinzel', serif;">${{ "{:,.2f}".format(stats.median_jackpot) }}</div>
                                        <div style="font-size: 0.8em; color: rgba(244, 232, 208, 0.7);">Median</div>
                                    </div>
                                    <div>
                                        <div style="font-size: 1.3em; color: #00ff9f; font-family: 'Cinzel', serif;">${{ "{:,.2f}".format(stats.max_jackpot) }}</div>
                                        <div style="font-size: 0.75em; color: rgba(244, 232, 208, 0.7);">Max Payout</div>
                                    </div>
                                    <div>
                                        <div style="font-size: 1.3em; color: var(--parchment); font-family: 'Cinzel', serif;">{{ "{:,}".format(stats.total_jackpots) }}</div>
                                        <div style="font-size: 0.75em; color: rgba(244, 232, 208, 0.7);">Total Hits</div>
                                    </div>
                                </div>
                            </div>
                            
                            <!-- Activity Tracker -->
                            <div style="background: linear-gradient(135deg, rgba(212, 175, 55, 0.1), rgba(205, 127, 50, 0.05)); padding: 12px; border-radius: 8px; margin-top: 15px;">
                                <h4 style="font-family: 'Cinzel', serif; font-size: 0.95em; color: var(--gold); margin-bottom: 10px; text-align: center;">🔥 Live Activity (15min intervals)</h4>
                                <div style="display: flex; gap: 3px; margin-bottom: 8px;">
                                    {% for activity in stats.activity_by_time %}
                                    {% set max_height = 40 %}
                                    {% set max_count = stats.activity_by_time|map(attribute='count')|max %}
                                    {% set height = (activity.count / max_count * max_height) if max_count > 0 else 5 %}
                                    <div style="flex: 1; display: flex; flex-direction: column; align-items: center;">
                                        <div style="width: 100%; background: linear-gradient(to top, var(--gold), var(--bronze)); height: {{ height }}px; border-radius: 2px 2px 0 0; position: relative;">
                                            {% if activity.count > 0 %}
                                            <div style="position: absolute; top: -18px; left: 50%; transform: translateX(-50%); font-size: 0.7em; color: var(--gold); font-weight: 700; white-space: nowrap;">{{ activity.count }}</div>
                                            {% endif %}
                                        </div>
                                    </div>
                                    {% endfor %}
                                </div>
                                <div style="display: flex; justify-content: space-between; font-size: 0.65em; color: rgba(244, 232, 208, 0.6);">
                                    <span>{{ stats.activity_by_time[0].label if stats.activity_by_time else '2h ago' }}</span>
                                    <span>{{ stats.activity_by_time[-1].label if stats.activity_by_time else 'Now' }}</span>
                                </div>
                            </div>

                             <!-- Recommended Machines -->
                            <h3 style="font-family: 'Cinzel', serif; font-size: 1.1em; color: #00ff9f; margin-top: 20px; margin-bottom: 10px; border-bottom: 2px solid #00ff9f; padding-bottom: 5px;">⭐ PLAY THESE NOW</h3>
                            <p style="font-size: 0.8em; color: rgba(244, 232, 208, 0.6); margin-bottom: 10px;">Best combo of frequency + payout</p>
                            {% for rec in stats.recommended[:5] %}
                            <div style="padding: 10px; margin: 8px 0; background: linear-gradient(90deg, rgba(0, 255, 159, 0.15), rgba(0, 255, 159, 0.05)); border-left: 4px solid #00ff9f; border-radius: 4px;">
                                <div style="margin-bottom: 5px;">
                                    <a href="/machine/{{ rec.machine_name }}" style="color: #00ff9f; font-weight: 700; font-size: 0.95em; text-decoration: none; border-bottom: 1px dotted #00ff9f;">{{ rec.machine_name[:35] }}</a>
                                </div>
                                <div style="display: flex; justify-content: space-between; font-size: 0.85em;">
                                    <span style="color: rgba(244, 232, 208, 0.9);">{{ rec.denomination }}</span>
                                    <span style="color: var(--gold); font-weight: 700;">Avg: ${{ "{:,.2f}".format(rec.avg_payout) }}</span>
                                </div>
                                <div style="font-size: 0.75em; color: rgba(244, 232, 208, 0.7); margin-top: 3px;">{{ "{:,}".format(rec.hit_count) }} hits • Max: ${{ "{:,.2f}".format(rec.max_payout) }}</div>
                            </div>
                            {% endfor %}

                        </div>
                    </div>
                    <!-- Column 2: Segments & Analytics -->
                    <div class="col-md-4">
                        <div class="scroll-card">
                            <h2 class="card-title">🔍 Market Segments</h2>

                            <!-- High Limit Room -->
                            <div style="background: linear-gradient(135deg, rgba(255, 215, 0, 0.2), rgba(255, 215, 0, 0.05)); padding: 15px; border-radius: 8px; margin-bottom: 25px; border: 2px solid gold;">
                                <h3 style="font-family: 'Cinzel', serif; font-size: 1.2em; color: gold; margin-bottom: 5px; text-align: center; text-shadow: 0 0 10px rgba(255, 215, 0, 0.5);">👑 HIGH LIMIT ROOM 👑</h3>
                                <p style="font-size: 0.75em; color: rgba(244, 232, 208, 0.8); text-align: center; margin-bottom: 15px;">
                                    HD Floor Location • <a href="/zone/HD" style="color: #00ff9f; text-decoration: underline;">View Report</a>
                                </p>
                                
                                <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; text-align: center; margin-bottom: 15px;">
                                    <div>
                                        <div style="font-size: 1.3em; color: gold; font-family: 'Cinzel', serif;">{{ "{:,}".format(stats.high_limit.count) }}</div>
                                        <div style="font-size: 0.7em; color: rgba(244, 232, 208, 0.7);">Total Hits</div>
                                    </div>
                                    <div>
                                        <div style="font-size: 1.3em; color: gold; font-family: 'Cinzel', serif;">${{ "{:,.0f}".format(stats.high_limit.avg) }}</div>
                                        <div style="font-size: 0.7em; color: rgba(244, 232, 208, 0.7);">Avg Payout</div>
                                    </div>
                                    <div>
                                        <div style="font-size: 1.3em; color: #00ff9f; font-family: 'Cinzel', serif;">${{ "{:,.0f}".format(stats.high_limit.max) }}</div>
                                        <div style="font-size: 0.7em; color: rgba(244, 232, 208, 0.7);">Max Hit</div>
                                    </div>
                                </div>
                                
                                {% if stats.high_limit.recommended %}
                                <h4 style="font-size: 0.9em; color: gold; margin-top: 15px; margin-bottom: 8px; border-bottom: 1px solid gold; padding-bottom: 3px;">⭐ Best High-Limit Machines</h4>
                                {% for hl in stats.high_limit.recommended[:3] %}
                                <div style="padding: 8px; margin: 5px 0; background: linear-gradient(90deg, rgba(255, 215, 0, 0.15), rgba(255, 215, 0, 0.05)); border-left: 3px solid gold; border-radius: 3px;">
                                    <div style="margin-bottom: 3px;">
                                        <a href="/machine/{{ hl.machine_name }}" style="color: gold; fontWeight: 700; fontSize: 0.8em; text-decoration: none; border-bottom: 1px dotted gold;">{{ hl.machine_name[:30] }}</a>
                                    </div>
                                    <div style="display: flex; justify-content: space-between; font-size: 0.75em;">
                                        <span style="color: rgba(244, 232, 208, 0.8);">{{ hl.denomination }}</span>
                                        <span style="color: #00ff9f; font-weight: 700;">${{ "{:,.0f}".format(hl.avg_payout) }}</span>
                                    </div>
                                    <div style="font-size: 0.7em; color: rgba(244, 232, 208, 0.6); margin-top: 2px;">{{ "{:,}".format(hl.hit_count) }} hits • Max: ${{ "{:,.0f}".format(hl.max_payout) }}</div>
                                </div>
                                {% endfor %}
                                {% endif %}
                            </div>
                            
                            <!-- Regular Floor Stats -->
                            <div style="background: linear-gradient(135deg, rgba(32, 201, 151, 0.2), rgba(32, 201, 151, 0.05)); padding: 15px; border-radius: 8px; margin-top: 25px; border: 2px solid #20c997;">
                                <h3 style="font-family: 'Cinzel', serif; font-size: 1.2em; color: #20c997; margin-bottom: 5px; text-align: center; text-shadow: 0 0 10px rgba(32, 201, 151, 0.5);">🎰 REGULAR FLOOR 🎰</h3>
                                <p style="font-size: 0.75em; color: rgba(244, 232, 208, 0.8); text-align: center; margin-bottom: 15px;">
                                    All Non-HD Locations • Regular Floor Machines
                                </p>
                                
                                <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; text-align: center; margin-bottom: 15px;">
                                    <div>
                                        <div style="font-size: 1.3em; color: #20c997; font-family: 'Cinzel', serif;">{{ "{:,}".format(stats.regular_floor.count) if stats.regular_floor and stats.regular_floor.count else '0' }}</div>
                                        <div style="font-size: 0.7em; color: rgba(244, 232, 208, 0.7);">Total Hits</div>
                                    </div>
                                    <div>
                                        <div style="font-size: 1.3em; color: #20c997; font-family: 'Cinzel', serif;">${{ "{:,.0f}".format(stats.regular_floor.avg) if stats.regular_floor and stats.regular_floor.avg else '0' }}</div>
                                        <div style="font-size: 0.7em; color: rgba(244, 232, 208, 0.7);">Avg Payout</div>
                                    </div>
                                    <div>
                                        <div style="font-size: 1.3em; color: var(--gold); font-family: 'Cinzel', serif;">${{ "{:,.0f}".format(stats.regular_floor.max) if stats.regular_floor and stats.regular_floor.max else '0' }}</div>
                                        <div style="font-size: 0.7em; color: rgba(244, 232, 208, 0.7);">Max Hit</div>
                                    </div>
                                </div>
                                
                                {% if stats.regular_floor and stats.regular_floor.recommended %}
                                <h4 style="font-size: 0.9em; color: #20c997; margin-top: 15px; margin-bottom: 8px; border-bottom: 1px solid #20c997; padding-bottom: 3px;">⭐ Best Regular Floor Machines</h4>
                                {% for rf in stats.regular_floor.recommended[:3] %}
                                <div style="padding: 8px; margin: 5px 0; background: linear-gradient(90deg, rgba(32, 201, 151, 0.15), rgba(32, 201, 151, 0.05)); border-left: 3px solid #20c997; border-radius: 3px;">
                                    <div style="margin-bottom: 3px;">
                                        <a href="/machine/{{ rf.machine_name }}" style="color: #20c997; font-weight: 700; font-size: 0.8em; text-decoration: none; border-bottom: 1px dotted #20c997;">{{ rf.machine_name[:30] }}</a>
                                    </div>
                                    <div style="display: flex; justify-content: space-between; font-size: 0.75em;">
                                        <span style="color: rgba(244, 232, 208, 0.8);">{{ rf.denomination }}</span>
                                        <span style="color: var(--gold); font-weight: 700;">${{ "{:,.0f}".format(rf.avg_payout) }}</span>
                                    </div>
                                    <div style="font-size: 0.7em; color: rgba(244, 232, 208, 0.6); margin-top: 2px;">{{ "{:,}".format(rf.hit_count) }} hits • Max: ${{ "{:,.0f}".format(rf.max_payout) }}</div>
                                </div>
                                {% endfor %}
                                {% endif %}
                            </div>

                             <!-- Hourly Trends -->
                            <h3 style="font-family: 'Cinzel', serif; font-size: 1.1em; color: var(--gold); margin-top: 25px; margin-bottom: 15px;">🕘 Hourly Activity Volume</h3>
                            <div id="hourly-chart" style="display: flex; align-items: flex-end; height: 100px; gap: 2px; margin-bottom: 25px; border-bottom: 1px solid rgba(255,255,255,0.1);">
                                {% for h in hourly %}
                                <div title="{{ h.hits }} hits at {{ h.hour }}:00" 
                                     style="flex: 1; background: {% if h.hits > 300 %}var(--accent){% else %}var(--bronze){% endif %}; 
                                            height: {{ (h.hits / 500 * 100)|int }}%; opacity: 0.8; border-radius: 2px 2px 0 0;"></div>
                                {% endfor %}
                            </div>

                            <!-- Anomaly Detection -->
                            <h3 style="font-size: 1.1em; color: #ff6b6b; margin-bottom: 15px;">🚨 Anomalies (Outliers)</h3>
                            <div id="outliers-list" style="max-height: 300px; overflow-y: auto;">
                                {% for o in outliers %}
                                <div style="background: rgba(255,0,0,0.1); border-left: 3px solid #ff4444; padding: 10px; margin-bottom: 10px;">
                                    <div style="display: flex; justify-content: space-between;">
                                        <a href="/machine/{{ o.machine_name }}" style="font-weight: bold; font-size: 0.9em; color: #fff; text-decoration: none;">{{ o.machine_name }}</a>
                                        <span class="badge bg-danger">Z: {{ o.z_score }}</span>
                                    </div>
                                    <div style="display: flex; justify-content: space-between; margin-top: 5px; font-size: 0.8em;">
                                        <span style="color: var(--accent);">${{ "{:,.2f}".format(o.amount) }}</span>
                                        <span class="text-muted">{{ o.hit_timestamp.strftime('%m/%d %I:%M%p') }}</span>
                                    </div>
                                </div>
                                {% endfor %}
                            </div>

                        </div>
                    </div>
                    <!-- Column 3: Strategy & Best Times -->
                    <div class="col-md-4">
                        <div class="scroll-card">
                            <h2 class="card-title">⚔️ Strategic Warfare</h2>
                            
                            <!-- Best Time to Play (Moved here, 24h list) -->
                            <h3 style="font-family: 'Cinzel', serif; font-size: 1.1em; color: var(--gold); margin-bottom: 10px; border-bottom: 1px solid var(--bronze); padding-bottom: 5px;">⏰ Best Time to Play (All-Time)</h3>
                            <p style="font-size: 0.75em; color: rgba(244, 232, 208, 0.6); margin-bottom: 10px;">Based on all historical jackpot frequency</p>
                            <div style="max-height: 400px; overflow-y: auto; margin-bottom: 25px; padding-right: 5px;">
                                {% for hour in stats.best_hours %}
                                <div style="padding: 8px; margin: 4px 0; background: linear-gradient(90deg, rgba(212, 175, 55, 0.1), rgba(205, 127, 50, 0.05)); border-left: 3px solid var(--gold); display: flex; justify-content: space-between; align-items: center;">
                                    <div>
                                        <div style="color: var(--gold); font-weight: 700; font-size: 0.9em;">{{ hour.time }}</div>
                                        <div style="color: rgba(244, 232, 208, 0.7); font-size: 0.75em;">{{ hour.hits }} hits</div>
                                    </div>
                                    <div style="color: var(--bronze); font-size: 0.85em;">${{ "%.0f"|format(hour.avg_payout) }}</div>
                                </div>
                                {% endfor %}
                            </div>

                            <!-- Zone Analysis -->
                            <h4 style="font-size: 0.95em; color: var(--parchment); margin-bottom: 10px; border-left: 3px solid var(--bronze); padding-left: 8px;">📍 Zone Control</h4>
                            <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 20px;">
                                {% for zone in stats.zones %}
                                <a href="/zone/{{ zone.zone }}" style="text-decoration: none; color: inherit; flex: 1; min-width: 45%;">
                                    <div style="background: rgba(0, 0, 0, 0.3); padding: 8px; border-radius: 4px; border: 1px solid rgba(212, 175, 55, 0.2); transition: all 0.2s;">
                                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                                            <span style="color: var(--gold); font-weight: 700;">{{ zone.zone }} {% if zone.zone == 'HD' %}(Hi-Lim){% endif %}</span>
                                            <span style="font-size: 0.8em; color: rgba(244, 232, 208, 0.6);">{{ zone.hits }} hits</span>
                                        </div>
                                        <div style="font-size: 0.8em; color: var(--bronze);">Avg: ${{ "%.0f"|format(zone.avg_payout) }}</div>
                                    </div>
                                </a>
                                {% endfor %}
                            </div>

                            <!-- Regular Zone Analysis -->
                            <h4 style="font-size: 0.95em; color: var(--parchment); margin-bottom: 10px; border-left: 3px solid #00ff9f; padding-left: 8px;">📍 Regular Floor (No High-Limit)</h4>
                            <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 20px;">
                                {% for zone in stats.zones_regular %}
                                <a href="/zone/{{ zone.zone }}" style="text-decoration: none; color: inherit; flex: 1; min-width: 45%;">
                                    <div style="background: rgba(0, 0, 0, 0.3); padding: 8px; border-radius: 4px; border: 1px solid rgba(0, 255, 159, 0.2); transition: all 0.2s;">
                                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                                            <span style="color: #00ff9f; font-weight: 700;">{{ zone.zone }}</span>
                                            <span style="font-size: 0.8em; color: rgba(244, 232, 208, 0.6);">{{ zone.hits }} hits</span>
                                        </div>
                                        <div style="font-size: 0.8em; color: var(--bronze);">Avg: ${{ "%.0f"|format(zone.avg_payout) }}</div>
                                    </div>
                                </a>
                                {% endfor %}
                            </div>
                            
                            <!-- Brand Wars -->
                            <h4 style="font-size: 0.95em; color: var(--parchment); margin-bottom: 10px; border-left: 3px solid var(--bronze); padding-left: 8px;">🐂 Battle of Brands</h4>
                            {% for family in stats.game_families %}
                            <a href="/brand/{{ family.family }}" style="text-decoration: none; color: inherit; display: block;">
                                <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 0; border-bottom: 1px solid rgba(212, 175, 55, 0.1);">
                                    <span style="color: rgba(244, 232, 208, 0.8); font-size: 0.9em;">{{ family.family }}</span>
                                    <div style="text-align: right;">
                                        <div style="color: var(--gold); font-size: 0.85em; font-weight: 700;">${{ "{:,.0f}".format(family.avg_payout) }}</div>
                                        <div style="color: rgba(244, 232, 208, 0.5); font-size: 0.75em;">{{ "{:,}".format(family.hits) }} hits</div>
                                    </div>
                                </div>
                            </a>
                            {% endfor %}
                            
                            <!-- Manufacturing War -->
                            <h4 style="font-size: 0.95em; color: var(--accent); margin-top: 20px; margin-bottom: 10px; border-left: 3px solid var(--accent); padding-left: 8px;">⚔️ Clash of Manufacturers</h4>
                            {% for mfg in stats.manufacturers %}
                            <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 0; border-bottom: 1px solid rgba(32, 201, 151, 0.2);">
                                <span style="color: rgba(244, 232, 208, 0.9); font-size: 0.9em; font-weight: bold;">{{ mfg.name }}</span>
                                <div style="text-align: right;">
                                    <div style="color: var(--accent); font-size: 0.85em; font-weight: 700;">${{ "{:,.0f}".format(mfg.total) }}</div>
                                    <div style="color: rgba(244, 232, 208, 0.5); font-size: 0.75em;">{{ "{:,}".format(mfg.hits) }} hits | Avg: ${{ "{:,.0f}".format(mfg.avg) }}</div>
                                </div>
                            </div>
                            {% endfor %}
                            
                            <!-- Sleeping Giants -->
                            {% if stats.cold_machines %}
                            <h4 style="font-size: 0.95em; color: #ff6b6b; margin-top: 20px; margin-bottom: 10px; border-left: 3px solid #ff6b6b; padding-left: 8px;">🧊 Sleeping Giants (Due?)</h4>
                            {% for machine in stats.cold_machines %}
                            <div style="padding: 8px; margin: 5px 0; background: linear-gradient(90deg, rgba(255, 107, 107, 0.1), rgba(255, 107, 107, 0.02)); border-left: 3px solid #ff6b6b;">
                                <div style="color: rgba(244, 232, 208, 0.9); font-size: 0.85em; margin-bottom: 3px;">{{ machine.machine_name[:30] }}...</div>
                                <div style="display: flex; justify-content: space-between; font-size: 0.75em;">
                                    <span style="color: #ff6b6b;">Cold for: {{ machine.time_since }}</span>
                                    <span style="color: rgba(244, 232, 208, 0.5);">{{ machine.historic_hits }} past hits</span>
                                </div>
                            </div>
                            {% endfor %}
                            {% endif %}
                            
                            <!-- Best Payouts -->
                            <h3 style="font-family: 'Cinzel', serif; font-size: 1.1em; color: var(--gold); margin-top: 20px; margin-bottom: 10px; border-bottom: 1px solid var(--bronze); padding-bottom: 5px;">
                                <a href="/payouts" style="color: inherit; text-decoration: none; display: flex; align-items: center; justify-content: space-between;">
                                    <span>💰 Highest Avg Payouts</span>
                                    <span style="font-size: 0.7em; opacity: 0.7;">View Top 100 →</span>
                                </a>
                            </h3>
                            {% for machine in stats.best_machines[:5] %}
                            <div style="padding: 8px; margin: 5px 0; background: linear-gradient(90deg, rgba(212, 175, 55, 0.1), rgba(205, 127, 50, 0.05)); border-left: 3px solid var(--gold);">
                                <div style="margin-bottom: 3px;">
                                    <a href="/machine/{{ machine.machine_name }}" style="color: var(--parchment); font-size: 0.85em; text-decoration: none;">{{ machine.machine_name[:30] }}...</a>
                                </div>
                                <div style="display: flex; justify-content: space-between; font-size: 0.8em;">
                                    <span style="color: rgba(244, 232, 208, 0.7);">{{ machine.denomination }}</span>
                                    <span style="color: var(--gold); font-weight: 700;">${{ "%.2f"|format(machine.avg_payout) }}</span>
                                </div>
                            </div>
                            {% endfor %}
                            
                            <!-- Hot Machines (Most Frequent) -->
                            <h3 style="font-family: 'Cinzel', serif; font-size: 1.1em; color: var(--gold); margin-top: 20px; margin-bottom: 10px; border-bottom: 1px solid var(--bronze); padding-bottom: 5px;">
                                <a href="/hottest" style="color: inherit; text-decoration: none; display: flex; align-items: center; justify-content: space-between;">
                                    <span>🔥 Hottest Machines</span>
                                    <span style="font-size: 0.7em; opacity: 0.7;">View All →</span>
                                </a>
                            </h3>
                            {% for machine in stats.top_machines[:5] %}
                            <div style="padding: 8px; margin: 5px 0; background: linear-gradient(90deg, rgba(212, 175, 55, 0.1), rgba(205, 127, 50, 0.05)); border-left: 3px solid var(--gold);">
                                <div style="color: {{ machine.color|default('#ffffff') }}; font-weight: bold; font-size: 0.85em; margin-bottom: 3px;">{{ machine.machine_name[:30] }}...</div>
                                <div style="display: flex; justify-content: space-between; font-size: 0.8em;">
                                    <span style="color: var(--bronze);">{{ machine.hit_count }} hits</span>
                                    <span style="color: var(--gold);">Avg: ${{ "%.2f"|format(machine.avg_payout) }}</span>
                                </div>
                            </div>
                            {% endfor %}
                            
                            <!-- Best Denominations -->
                            <h3 style="font-family: 'Cinzel', serif; font-size: 1.1em; color: var(--gold); margin-top: 20px; margin-bottom: 10px; border-bottom: 1px solid var(--bronze); padding-bottom: 5px;">💵 Best Bet Sizes</h3>
                            {% for denom in stats.top_denoms[:5] %}
                            <a href="/denom/{{ denom.denomination }}" style="text-decoration: none; color: inherit; display: block;">
                                <div style="padding: 8px; margin: 5px 0; background: linear-gradient(90deg, rgba(212, 175, 55, 0.1), rgba(205, 127, 50, 0.05)); border-left: 3px solid var(--gold); display: flex; justify-content: space-between;">
                                    <span style="color: var(--parchment);">{{ denom.denomination }}</span>
                                    <span style="color: var(--gold); font-weight: 700;">${{ "%.2f"|format(denom.avg_payout) }}</span>
                                </div>
                            </a>
                            {% endfor %}
                        </div>
                    </div>
                </div>
            </div>
        </div>


    </div>
    
    <div class="footer">
        <div><span>⚔</span> <span>SYSTEM ONLINE</span></div>
        <div style="color: var(--gold); font-family: 'Cinzel', serif;">📜 Analyzing {{ stats.total_jackpots }} Data Points</div>
        <div><span>Last Updated: {{ update_time }}</span></div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // Charts removed in new layout
        setTimeout(() => location.reload(), 300000);
        let timeLeft = 300;
        setInterval(() => { timeLeft--; if (timeLeft <= 0) timeLeft = 300; const m = Math.floor(timeLeft / 60), s = timeLeft % 60; document.title = `⚔ The One Dashboard (${m}:${s.toString().padStart(2, '0')})`; }, 1000);
    </script>
</body>
</html>
"""

@app.route('/')
@cache.cached(timeout=300)
def index():
    trending_us = get_trending_searches('united_states')
    trending_global = get_trending_searches('worldwide')
    news_data = get_news()
    services = get_services()
    
    jackpots_raw = get_jackpots()
    jackpots_data = []
    for jp in jackpots_raw[:100]:  # Show more jackpots
        jackpots_data.append({
            'location_id': jp.get('location_id', 'Unknown'),
            'machine_name': jp.get('machine_name', 'Unknown')[:50],
            'denomination': jp.get('denomination', 'Unknown'),
            'amount': jp.get('amount'),
            'timestamp': jp.get('hit_timestamp'),
            'time_ago': format_time_ago(jp.get('hit_timestamp') or jp.get('scraped_at'))
        })
    
    # Get casino statistics
    stats = get_jackpot_stats()
    
    # Charts removed
    update_time = datetime.now().strftime('%H:%M:%S')
    
    multi_casino = get_multi_casino_stats()
    
    return render_template_string(HTML_TEMPLATE, trending_us=trending_us, trending_global=trending_global,
                                 news_data=news_data, services=services, jackpots_data=jackpots_data,
                                 stats=stats, multi_casino=multi_casino, update_time=update_time)


@app.route('/best-times')
def best_times_detail():
    hourly_data = get_hourly_details()
    if not hourly_data:
        return "Error loading data", 500
        
    template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Best Time to Play Analysis</title>
        {{ styles|safe }}
    </head>
    <body>
        <div class="container">
            <a href="/" class="back-btn">← Back to Treasure Hunter</a>
            
            <h1 class="mb-4 text-center">⏰ 24-Hour Jackpot Cycle</h1>
            
            <!-- Chart -->
            <div class="card p-3 mb-4">
                <canvas id="hourlyChart" height="100"></canvas>
            </div>
            
            <!-- Data Table -->
            <div class="card p-4">
                <h3 class="mb-3">Detailed Hourly Breakdown</h3>
                <div class="table-responsive">
                    <table class="table table-dark table-hover">
                        <thead>
                            <tr style="color: var(--text-gold); border-bottom: 2px solid #555;">
                                <th>Hour</th>
                                <th>Hit Frequency</th>
                                <th>Avg Payout</th>
                                <th>Max Win Recorded</th>
                                <th>Total Paid Out</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for row in data %}
                            <tr style="{% if row.hits > (data|map(attribute='hits')|max * 0.8) %}background: rgba(212, 175, 55, 0.15);{% endif %}">
                                <td style="font-weight: bold;">{{ row.label }}</td>
                                <td>
                                    <div style="display: flex; align-items: center; gap: 10px;">
                                        <div style="width: 100px; background: rgba(255,255,255,0.1); height: 8px; border-radius: 4px;">
                                            <div style="width: {{ (row.hits / (data|map(attribute='hits')|max) * 100)|int }}%; background: var(--text-gold); height: 100%; border-radius: 4px;"></div>
                                        </div>
                                        {{ "{:,}".format(row.hits) }}
                                    </div>
                                </td>
                                <td style="color: var(--accent);">${{ "{:,.0f}".format(row.avg) }}</td>
                                <td>${{ "{:,.0f}".format(row.max) }}</td>
                                <td>${{ "{:,.0f}".format(row.total) }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <script>
            const ctx = document.getElementById('hourlyChart').getContext('2d');
            const data = {{ data|tojson }};
            
            new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: data.map(d => d.label),
                    datasets: [
                        {
                            label: 'Jackpot Hits',
                            data: data.map(d => d.hits),
                            backgroundColor: 'rgba(212, 175, 55, 0.6)',
                            borderColor: 'rgba(212, 175, 55, 1)',
                            borderWidth: 1,
                            yAxisID: 'y'
                        },
                        {
                            label: 'Avg Payout ($)',
                            data: data.map(d => d.avg),
                            type: 'line',
                            borderColor: '#20c997',
                            pointBackgroundColor: '#20c997',
                            borderWidth: 2,
                            tension: 0.4,
                            yAxisID: 'y1'
                        }
                    ]
                },
                options: {
                    responsive: true,
                    interaction: {
                        mode: 'index',
                        intersect: false,
                    },
                    scales: {
                        y: {
                            type: 'linear',
                            display: true,
                            position: 'left',
                            grid: { color: 'rgba(255,255,255,0.1)' },
                            title: { display: true, text: 'Number of Jackpots' }
                        },
                        y1: {
                            type: 'linear',
                            display: true,
                            position: 'right',
                            grid: { drawOnChartArea: false },
                            title: { display: true, text: 'Average Payout ($)' }
                        },
                        x: {
                            grid: { display: false }
                        }
                    },
                    plugins: {
                        legend: { labels: { color: '#ccc' } }
                    }
                }
            });
        </script>
    </body>
    </html>
    """
    return render_template_string(template, data=hourly_data, styles=SHARED_STYLES)


@app.route('/api/analytics')
def api_analytics():
    """API endpoint for real-time analytics updates"""
    return jsonify({
        'hourly': get_hourly_analytics(),
        'outliers': get_jackpot_outliers(),
        'clusters': get_jackpot_clusters(),
        'banks': get_hot_banks()
    })

@app.route('/payouts')
def payouts_ranking():
    machines = get_all_machine_stats()
    stats = get_jackpot_stats() # reuse for global stats if needed
    
    template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Machine Rankings & Payouts</title>
        {{ styles|safe }}
    </head>
    <body>
        <div class="container">
            <a href="/" style="font-size: 1.1em; margin-bottom: 20px; display: inline-block;">← Back to Treasure Hunter</a>
            
            <h1 class="mb-4 text-center">🏆 Highest Paying Machines</h1>
            <p class="text-center" style="color: #888; margin-top: -10px; margin-bottom: 30px;">Top 100 Machines ranked by Average Payout (Min. 2 hits)</p>
            
            <div class="card p-4">
                <div class="table-responsive">
                    <table class="table table-dark table-hover align-middle">
                        <thead>
                            <tr style="color: var(--text-gold); border-bottom: 2px solid #555;">
                                <th style="width: 60px;">Rank</th>
                                <th>Machine Name</th>
                                <th>Zone</th>
                                <th class="text-end">Avg Payout</th>
                                <th class="text-end">Max Win</th>
                                <th class="text-end">Total Hits</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for m in machines %}
                            <tr style="cursor: pointer;" onclick="window.location='/machine/{{ m.machine_name }}'">
                                <td>
                                    <div class="rank-badge rank-{{ loop.index }}">{{ loop.index }}</div>
                                </td>
                                <td>
                                    <div style="font-weight: bold; color: var(--text-light);">{{ m.machine_name }}</div>
                                    <div style="font-size: 0.8em; color: #666;">Last hit: {{ m.last_hit.strftime('%m/%d') }}</div>
                                </td>
                                <td><span class="badge bg-secondary" style="background: rgba(255,255,255,0.1) !important; color: #aaa;">{{ m.location_id }}</span></td>
                                <td class="text-end" style="font-size: 1.1em; color: var(--accent); font-weight: bold;">${{ "{:,.0f}".format(m.avg_payout) }}</td>
                                <td class="text-end" style="color: #ccc;">${{ "{:,.0f}".format(m.max_payout) }}</td>
                                <td class="text-end">
                                    <span style="background: rgba(212, 175, 55, 0.2); color: var(--text-gold); padding: 2px 8px; border-radius: 10px; font-size: 0.9em;">{{ "{:,}".format(m.hits) }}</span>
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return render_template_string(template, machines=machines, stats=stats, styles=SHARED_STYLES)

@app.route('/machine/<path:machine_name>')
def machine_detail(machine_name):
    # Decode URL-encoded machine name if necessary, though Flask handles path variables well
    print(f"DEBUG: Machine route called with: '{machine_name}'")
    try:
        details = get_machine_details(machine_name)
        print(f"DEBUG: get_machine_details returned: {details is not None}")
        if not details:
            print(f"DEBUG: No details found for '{machine_name}'")
            return "Machine not found", 404
    except Exception as e:
        print(f"ERROR in machine_detail: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return f"Error: {str(e)}", 500
        
    # Use a simpler template for the popup/drilldown
    MACHINE_TEMPLATE = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{{ details.summary.machine_name }} - Analysis</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@400;700&family=Lato:wght@300;400;700&display=swap" rel="stylesheet">
        <style>
            :root {
                --bg-dark: #0f1115;
                --card-bg: #1a1d23;
                --text-main: #e0e0e0;
                --gold: #d4af37;
                --bronze: #cd7f32;
                --accent: #00ff9f;
            }
            body {
                background-color: var(--bg-dark);
                color: var(--text-main);
                font-family: 'Lato', sans-serif;
                padding: 20px;
            }
            .metric-card {
                background: linear-gradient(145deg, #1a1d23, #22262e);
                border: 1px solid rgba(212, 175, 55, 0.2);
                border-radius: 8px;
                padding: 15px;
                text-align: center;
                box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            }
            .metric-value { font-family: 'Cinzel', serif; font-size: 1.5em; color: var(--gold); }
            .metric-label { font-size: 0.8em; color: rgba(255,255,255,0.6); text-transform: uppercase; letter-spacing: 1px; }
            h1, h2, h3 { font-family: 'Cinzel', serif; color: var(--gold); }
            .table-dark { background-color: var(--card-bg); --bs-table-bg: var(--card-bg); border-color: rgba(255,255,255,0.1); }
            .back-btn { text-decoration: none; color: var(--bronze); font-size: 0.9em; display: inline-block; margin-bottom: 20px; transition: 0.2s; }
            .back-btn:hover { color: var(--gold); transform: translateX(-5px); }
        </style>
    </head>
    <body>
        <div class="container" style="max-width: 800px;">
            <a href="/" class="back-btn">← Back to Dashboard</a>
            
            <div style="border-bottom: 2px solid var(--gold); padding-bottom: 15px; margin-bottom: 25px;">
                <h1 style="margin-bottom: 5px;">{{ machine_name }}</h1>
                <div style="display: flex; flex-wrap: wrap; gap: 15px; color: rgba(255,255,255,0.7); font-size: 0.9em;">
                    {% if details.summary.manufacturer %}
                    <span>🏭 <strong style="color: var(--gold);">{{ details.summary.manufacturer }}</strong></span>
                    {% endif %}
                    <span>📍 Zone: <strong style="color: var(--accent);">{{ details.summary.location_id }}</strong></span>
                    <span>💵 Denom: <strong style="color: var(--accent);">{{ details.summary.denomination }}</strong></span>
                    {% if details.summary.volatility and details.summary.volatility != 'Unknown' %}
                    <span>⚡ Volatility: <strong style="color: {% if 'High' in details.summary.volatility|string %}#ff6b6b{% elif 'Low' in details.summary.volatility|string %}#51cf66{% else %}#ffd43b{% endif %};">{{ details.summary.volatility }}</strong></span>
                    {% endif %}
                    <span>🔥 Heat: <strong style="color: {% if 'HOT' in details.heat_rating %}#ff6b6b{% elif 'COLD' in details.heat_rating %}#4dabf7{% else %}#ffd43b{% endif %};">{{ details.heat_rating }}</strong></span>
                </div>
            </div>
            
            <!-- Machine Photo -->
            {% if details.summary.photo_url %}
            <div style="text-align: center; margin: 20px 0;">
                <img src="{{ details.summary.photo_url }}" alt="{{ machine_name }}" style="max-width: 300px; border-radius: 8px; box-shadow: 0 4px 12px rgba(212, 175, 55, 0.3);" />
            </div>
            {% endif %}

            <div class="row g-3 mb-4">
                <div class="col-6 col-md-3">
                    <div class="metric-card">
                        <div class="metric-value">${{ "{:,.0f}".format(details.summary.avg_payout) }}</div>
                        <div class="metric-label">Avg Win</div>
                    </div>
                </div>
                <div class="col-6 col-md-3">
                    <div class="metric-card">
                        <div class="metric-value">{{ details.pacing }}</div>
                        <div class="metric-label">Avg Wait (Pacing)</div>
                    </div>
                </div>
                <div class="col-6 col-md-3">
                    <div class="metric-card">
                        <div class="metric-value">{{ "{:,}".format(details.summary.total_hits) }}</div>
                        <div class="metric-label">Total Hits</div>
                    </div>
                </div>
                <div class="col-6 col-md-3">
                    <div class="metric-card">
                        <div class="metric-value">${{ "{:,.0f}".format(details.summary.max_payout) }}</div>
                        <div class="metric-label">Max Win</div>
                    </div>
                </div>
            </div>

            <div class="row mb-4">
                <div class="col-md-6">
                    <h3 style="font-size: 1.2em; border-bottom: 1px solid var(--bronze); padding-bottom: 8px; margin-bottom: 15px;">⏰ Best Times (Hourly)</h3>
                    {% if details.best_hours %}
                    <div class="list-group">
                        {% for hour in details.best_hours %}
                        <div class="list-group-item" style="background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); color: #ccc; display: flex; justify-content: space-between;">
                            <span>{{ hour.time }}</span>
                            <span><strong style="color: var(--gold);">{{ hour.hits }} hits</strong> <small>(${{ "{:,.0f}".format(hour.avg) }} avg)</small></span>
                        </div>
                        {% endfor %}
                    </div>
                    {% else %}
                    <p style="color: #666;">Not enough data yet.</p>
                    {% endif %}
                    
                    <h3 style="font-size: 1.2em; border-bottom: 1px solid var(--bronze); padding-bottom: 8px; margin: 25px 0 15px 0;">📊 Jackpot Range Analysis</h3>
                    {% for dist in details.distribution %}
                    <div style="margin-bottom: 8px;">
                        <div style="display: flex; justify-content: space-between; font-size: 0.9em; margin-bottom: 2px;">
                            <span style="color: rgba(255,255,255,0.9);">{{ dist.label }}</span>
                            <span style="color: var(--accent); font-weight: bold;">{{ dist.count }} hit{% if dist.count != 1 %}s{% endif %}</span>
                        </div>
                        <div style="background: rgba(255,255,255,0.1); height: 8px; border-radius: 4px; overflow: hidden;">
                            <div style="background: linear-gradient(90deg, var(--gold), var(--bronze)); width: {{ (dist.count / details.summary.total_hits * 100)|int }}%; height: 100%;"></div>
                        </div>
                    </div>
                    {% endfor %}
                </div>
                
                <div class="col-md-6">
                    <h3 style="font-size: 1.2em; border-bottom: 1px solid var(--bronze); padding-bottom: 8px; margin-bottom: 15px;">📜 Recent Hit History</h3>
                    <div style="max-height: 400px; overflow-y: auto;">
                        <table class="table table-dark table-sm" style="font-size: 0.9em;">
                            <thead>
                                <tr>
                                    <th style="color: var(--bronze);">Time</th>
                                    <th style="color: var(--bronze); text-align: right;">Amount</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for hit in details.history %}
                                <tr>
                                    <td>{{ hit.hit_timestamp.strftime('%m/%d %I:%M %p') }}</td>
                                    <td style="text-align: right; color: var(--accent);">${{ "{:,.2f}".format(hit.amount) }}</td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            
        </div>
    </body>
    </html>
    """
    return render_template_string(MACHINE_TEMPLATE, machine_name=machine_name, details=details, styles=SHARED_STYLES)

@app.route('/bank/<bank_id>')
def bank_details(bank_id):
    details = get_bank_details(bank_id)
    if not details:
        return f"Bank {bank_id} not found or no data", 404
        
    BANK_TEMPLATE = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Bank {{ details.summary.bank_id }} - Analysis</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@400;700&family=Lato:wght@300;400;700&display=swap" rel="stylesheet">
        <style>
            :root {
                --bg-dark: #0f1115;
                --card-bg: #1a1d23;
                --text-main: #e0e0e0;
                --gold: #d4af37;
                --bronze: #cd7f32;
                --accent: #00ff9f;
            }
            body {
                background-color: var(--bg-dark);
                color: var(--text-main);
                font-family: 'Lato', sans-serif;
                padding: 20px;
            }
            .metric-card {
                background: linear-gradient(145deg, #1a1d23, #22262e);
                border: 1px solid rgba(212, 175, 55, 0.2);
                border-radius: 8px;
                padding: 15px;
                text-align: center;
                box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            }
            .metric-value { font-family: 'Cinzel', serif; font-size: 1.5em; color: var(--gold); }
            .metric-label { font-size: 0.8em; color: rgba(255,255,255,0.6); text-transform: uppercase; letter-spacing: 1px; }
            h1, h2, h3 { font-family: 'Cinzel', serif; color: var(--gold); }
            .table-dark { background-color: var(--card-bg); --bs-table-bg: var(--card-bg); border-color: rgba(255,255,255,0.1); }
            .back-btn { text-decoration: none; color: var(--bronze); font-size: 0.9em; display: inline-block; margin-bottom: 20px; transition: 0.2s; }
            .back-btn:hover { color: var(--gold); transform: translateX(-5px); }
            a { text-decoration: none; color: var(--accent); }
            a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <div class="container" style="max-width: 900px;">
            <a href="/" class="back-btn">← Back to Dashboard</a>
            
            <div style="border-bottom: 2px solid var(--gold); padding-bottom: 15px; margin-bottom: 25px;">
                <h1 style="margin-bottom: 5px;">Bank {{ details.summary.bank_id }}</h1>
                <div style="color: rgba(255,255,255,0.7);">
                    Machines: <span style="color: #fff;">{{ details.summary.distinct_machines }}</span> | 
                    Last Active: <span style="color: var(--accent);">{{ details.summary.last_activity.strftime('%m/%d %I:%M %p') if details.summary.last_activity else 'N/A' }}</span>
                </div>
            </div>

            <div class="row g-3 mb-4">
                <div class="col-6 col-md-3">
                    <div class="metric-card">
                        <div class="metric-value">${{ "{:,.0f}".format(details.summary.avg_payout) }}</div>
                        <div class="metric-label">Avg Win</div>
                    </div>
                </div>
                <div class="col-6 col-md-3">
                    <div class="metric-card">
                        <div class="metric-value">{{ "{:,}".format(details.summary.total_hits) }}</div>
                        <div class="metric-label">Total Hits</div>
                    </div>
                </div>
                <div class="col-6 col-md-3">
                    <div class="metric-card">
                        <div class="metric-value">${{ "{:,.0f}".format(details.summary.max_payout) }}</div>
                        <div class="metric-label">Max Win</div>
                    </div>
                </div>
                <div class="col-6 col-md-3">
                    <div class="metric-card">
                        <div class="metric-value">${{ "{:,.0f}".format(details.summary.min_payout) }}</div>
                        <div class="metric-label">Min Win</div>
                    </div>
                </div>
            </div>

            <div class="row">
                <div class="col-12 mb-4">
                    <h3 style="font-size: 1.2em; border-bottom: 1px solid var(--bronze); padding-bottom: 8px; margin-bottom: 15px;">🎰 Machines in Bank</h3>
                    <div class="table-responsive">
                        <table class="table table-dark table-hover table-sm">
                            <thead>
                                <tr>
                                    <th style="color: var(--bronze);">Machine</th>
                                    <th style="color: var(--bronze);">Loc ID</th>
                                    <th style="color: var(--bronze);">Denom</th>
                                    <th style="color: var(--bronze); text-align: center;">Hits</th>
                                    <th style="color: var(--bronze); text-align: right;">Avg Payout</th>
                                    <th style="color: var(--bronze); text-align: right;">Max Payout</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for m in details.machines %}
                                <tr>
                                    <td><a href="/machine/{{ m.machine_name }}">{{ m.machine_name }}</a></td>
                                    <td>{{ m.location_id }}</td>
                                    <td>{{ m.denomination }}</td>
                                    <td style="text-align: center;">{{ m.hits }}</td>
                                    <td style="text-align: right;">${{ "{:,.0f}".format(m.avg_payout) }}</td>
                                    <td style="text-align: right;">${{ "{:,.0f}".format(m.max_payout) }}</td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>
                
                <div class="col-12">
                    <h3 style="font-size: 1.2em; border-bottom: 1px solid var(--bronze); padding-bottom: 8px; margin-bottom: 15px;">📜 Recent Bank Activity</h3>
                    <div class="table-responsive">
                        <table class="table table-dark table-sm">
                            <thead>
                                <tr>
                                    <th style="color: var(--bronze);">Time</th>
                                    <th style="color: var(--bronze);">Machine</th>
                                    <th style="color: var(--bronze); text-align: right;">Amount</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for hit in details.recent_hits %}
                                <tr>
                                    <td>{{ hit.hit_timestamp.strftime('%m/%d %I:%M %p') }}</td>
                                    <td>{{ hit.machine_name }}</td>
                                    <td style="text-align: right; color: var(--accent);">${{ "{:,.2f}".format(hit.amount) }}</td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            
        </div>
    </body>
    </html>
    """
    return render_template_string(BANK_TEMPLATE, details=details)

@app.route('/api/jackpots')
def api_jackpots():
    return jsonify(get_jackpots())


# Tabler Dashboard API Routes
@app.route('/api/high-limit-stats')
@cache.cached(timeout=300)
def api_high_limit_stats():
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database error'}), 500
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT 
                COUNT(*) as count,
                ROUND(AVG(amount), 2) as avg,
                MAX(amount) as max
            FROM jackpots
            WHERE location_id LIKE 'HD%'
        """)
        stats = dict(cur.fetchone() or {'count': 0, 'avg': 0, 'max': 0})
        
        cur.execute("""
            SELECT 
                machine_name,
                denomination,
                COUNT(*) as hit_count,
                ROUND(AVG(amount), 2) as avg_payout,
                MAX(amount) as max_payout,
                COUNT(*) FILTER (WHERE hit_timestamp > NOW() - INTERVAL '7 days') as hits_7d
            FROM jackpots
            WHERE location_id LIKE 'HD%'
            GROUP BY machine_name, denomination
            HAVING COUNT(*) >= 2 
                AND COUNT(*) FILTER (WHERE hit_timestamp > NOW() - INTERVAL '7 days') > 0
            ORDER BY COUNT(*) FILTER (WHERE hit_timestamp > NOW() - INTERVAL '7 days') * AVG(amount) DESC
            LIMIT 5
        """)
        machines = [dict(row) for row in cur.fetchall()]
        
        cur.close()
        conn.close()
        
        return jsonify({
            'stats': stats,
            'machines': machines,
            'updated_at': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/regular-floor-stats')
def api_regular_floor_stats():
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database error'}), 500
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT 
                COUNT(*) as count,
                ROUND(AVG(amount), 2) as avg,
                MAX(amount) as max
            FROM jackpots
            WHERE location_id NOT LIKE 'HD%' OR location_id IS NULL
        """)
        stats = dict(cur.fetchone() or {'count': 0, 'avg': 0, 'max': 0})
        
        cur.execute("""
            SELECT 
                machine_name,
                denomination,
                COUNT(*) as hit_count,
                ROUND(AVG(amount), 2) as avg_payout,
                MAX(amount) as max_payout,
                COUNT(*) FILTER (WHERE hit_timestamp > NOW() - INTERVAL '7 days') as hits_7d
            FROM jackpots
            WHERE location_id NOT LIKE 'HD%' OR location_id IS NULL
            GROUP BY machine_name, denomination
            HAVING COUNT(*) >= 3
                AND COUNT(*) FILTER (WHERE hit_timestamp > NOW() - INTERVAL '7 days') > 0
            ORDER BY COUNT(*) FILTER (WHERE hit_timestamp > NOW() - INTERVAL '7 days') * AVG(amount) DESC
            LIMIT 5
        """)
        machines = [dict(row) for row in cur.fetchall()]
        
        cur.execute("""
            SELECT
                SUBSTRING(location_id, 1, 2) as area_code,
                COUNT(*) as hit_count,
                ROUND(AVG(amount), 2) as avg_payout,
                COUNT(*) FILTER (WHERE hit_timestamp > NOW() - INTERVAL '24 hours') as hits_24h
            FROM jackpots
            WHERE location_id NOT LIKE 'HD%' AND location_id IS NOT NULL
            GROUP BY area_code
            HAVING COUNT(*) >= 10
            ORDER BY hits_24h DESC, avg_payout DESC
            LIMIT 8
        """)
        areas = [dict(row) for row in cur.fetchall()]
        
        cur.close()
        conn.close()
        
        return jsonify({
            'stats': stats,
            'machines': machines,
            'areas': areas,
            'updated_at': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/live-feed')
def api_live_feed():
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database error'}), 500
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT 
                machine_name,
                amount,
                denomination,
                location_id,
                hit_timestamp,
                scraped_at
            FROM jackpots
            ORDER BY hit_timestamp DESC NULLS LAST, scraped_at DESC
            LIMIT 20
        """)
        
        jackpots = [dict(row) for row in cur.fetchall()]
        
        cur.close()
        conn.close()
        
        return jsonify({
            'jackpots': jackpots,
            'updated_at': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Tabler Dashboard Route
@app.route('/jackpots')
def tabler_jackpots():
    """Modern Tabler-based jackpot dashboard with auto-refresh"""
    
    template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charsetutf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>🎰 Jackpot Dashboard - Coushatta Casino</title>
        
        <!-- Tabler CSS -->
        <link href="https://cdn.jsdelivr.net/npm/@tabler/core@latest/dist/css/tabler.min.css" rel="stylesheet"/>
        <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@400;700&display=swap" rel="stylesheet">
        
        <style>
            :root {
                --tblr-primary: #d4af37;
                --tblr-secondary: #cd7f32;
            }
            body {
                background: linear-gradient(135deg, #1a0f0a, #2c1810);
                font-family: system-ui, -apple-system, sans-serif;
            }
            .page-header {
                background: linear-gradient(135deg, rgba(212, 175, 55, 0.2), rgba(205, 127, 50, 0.1));
                border-bottom: 2px solid var(--tblr-primary);
            }
            .page-title {
                font-family: 'Cinzel', serif;
                color: var(--tblr-primary);
                text-shadow: 0 0 20px rgba(212, 175, 55, 0.5);
            }
            .card {
                background: rgba(43, 43, 43, 0.9);
                border: 1px solid rgba(212, 175, 55, 0.3);
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.5);
            }
            .card-header {
                background: linear-gradient(135deg, rgba(212, 175, 55, 0.2), rgba(205, 127, 50, 0.1));
                border-bottom: 1px solid rgba(212, 175, 55, 0.3);
            }
            .card-title {
                font-family: 'Cinzel', serif;
                color: var(--tblr-primary);
                font-weight: 700;
            }
            .text-gold { color: var(--tblr-primary) !important; }
            .machine-item {
                padding: 12px;
                margin: 8px 0;
                background: linear-gradient(90deg, rgba(212, 175, 55, 0.1), transparent);
                border-left: 3px solid var(--tblr-primary);
                border-radius: 4px;
                cursor: pointer;
                transition: all 0.3s;
            }
            .machine-item:hover {
                background: linear-gradient(90deg, rgba(212, 175, 55, 0.2), rgba(205, 127, 50, 0.1));
                transform: translateX(5px);
            }
            .area-badge {
                display: inline-block;
                padding: 4px 12px;
                background: linear-gradient(135deg, var(--tblr-primary), var(--tblr-secondary));
                color: #1a0f0a;
                border-radius: 4px;
                font-weight: 700;
                cursor: pointer;
                font-family: 'Cinzel', serif;
            }
            .jackpot-feed-item {
                padding: 10px;
                border-bottom: 1px solid rgba(212, 175, 55, 0.2);
                transition: background 0.2s;
            }
            .jackpot-feed-item:hover {
                background: rgba(212, 175, 55, 0.1);
            }
            .amount-large { color: #ff6b6b; font-weight: 700; font-size: 1.1em; }
            .amount-medium { color: #20c997; font-weight: 600; }
            .amount-small { color: #eaeaea; }
            .loading-overlay {
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.5);
                display: none;
                align-items: center;
                justify-content: center;
                z-index: 10;
            }
        </style>
    </head>
    <body>
        <div class="page">
            <!-- Header -->
            <header class="navbar navbar-expand-md navbar-dark d-print-none">
                <div class="container-xl">
                    <h1 class="navbar-brand navbar-brand-autodark d-none-navbar-horizontal pe-0 pe-md-3">
                        <span class="page-title">🎰 Jackpot Dashboard</span>
                    </h1>
                    <div class="navbar-nav flex-row order-md-last">
                        <div class="d-none d-md-flex">
                            <div class="nav-item dropdown">
                                <a href="/" class="nav-link">← Back to Main Dashboard</a>
                            </div>
                        </div>
                    </div>
                </div>
            </header>
            
            <!-- Page Content -->
            <div class="page-wrapper">
                <div class="container-xl">
                    <div class="page-header d-print-none">
                        <div class="row align-items-center">
                            <div class="col">
                                <h2 class="page-title">Coushatta Casino - Live Jackpot Monitoring</h2>
                                <div class="text-muted mt-1">Auto-updates every 30-120 seconds • <span id="last-update" class="text-gold">Loading...</span></div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="page-body">
                    <div class="container-xl">
                        <div class="row row-deck row-cards">
                            
                            <!-- High Limit Room Card -->
                            <div class="col-md-6">
                                <div class="card">
                                    <div class="card-header">
                                        <h3 class="card-title">👑 High Limit Room</h3>
                                        <div class="card-actions">
                                            <span class="badge bg-primary">$10,000+</span>
                                        </div>
                                    </div>
                                    <div class="card-body" id="high-limit-content">
                                        <div class="loading-overlay" style="display: flex;">
                                            <div class="spinner-border text-primary" role="status"></div>
                                        </div>
                                        <!-- Loaded via JS -->
                                    </div>
                                    <div class="card-footer text-muted">
                                        <small>Updates every 2 minutes</small>
                                    </div>
                                </div>
                            </div>
                            
                            <!-- Regular Floor Card -->
                            <div class="col-md-6">
                                <div class="card">
                                    <div class="card-header">
                                        <h3 class="card-title">🎰 Regular Floor</h3>
                                        <div class="card-actions">
                                            <span class="badge bg-secondary">Under $10,000</span>
                                        </div>
                                    </div>
                                    <div class="card-body" id="regular-floor-content">
                                        <div class="loading-overlay" style="display: flex;">
                                            <div class="spinner-border text-primary" role="status"></div>
                                        </div>
                                        <!-- Loaded via JS -->
                                    </div>
                                    <div class="card-footer text-muted">
                                        <small>Updates every 2 minutes</small>
                                    </div>
                                </div>
                            </div>
                            
                            <!-- Live Feed Card -->
                            <div class="col-12">
                                <div class="card">
                                    <div class="card-header">
                                        <h3 class="card-title">📡 Live Jackpot Feed</h3>
                                        <div class="card-actions">
                                            <span class="badge bg-success">Real-time</span>
                                        </div>
                                    </div>
                                    <div class="card-body" id="live-feed-content" style="max-height: 600px; overflow-y: auto;">
                                        <div class="loading-overlay" style="display: flex;">
                                            <div class="spinner-border text-primary" role="status"></div>
                                        </div>
                                        <!-- Loaded via JS -->
                                    </div>
                                    <div class="card-footer text-muted">
                                        <small>Updates every 30 seconds</small>
                                    </div>
                                </div>
                            </div>
                            
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Tabler JS -->
        <script src="https://cdn.jsdelivr.net/npm/@tabler/core@latest/dist/js/tabler.min.js"></script>
        
        <script>
            // Auto-refresh functions
            function updateHighLimit() {
                fetch('/api/high-limit-stats')
                    .then(r => r.json())
                    .then(data => {
                        const content = document.getElementById('high-limit-content');
                        content.querySelector('.loading-overlay').style.display = 'none';
                        
                        const stats = data.stats;
                        const machines = data.machines;
                        
                        let html = `
                            <div class="row mb-3">
                                <div class="col-4 text-center">
                                    <div class="h2 text-gold">${stats.count.toLocaleString()}</div>
                                    <div class="text-muted">Total Hits</div>
                                </div>
                                <div class="col-4 text-center">
                                    <div class="h2 text-gold">$${stats.avg.toLocaleString()}</div>
                                    <div class="text-muted">Avg Payout</div>
                                </div>
                                <div class="col-4 text-center">
                                    <div class="h2 text-success">$${stats.max.toLocaleString()}</div>
                                    <div class="text-muted">Max Hit</div>
                                </div>
                            </div>
                            <hr>
                            <h4 class="text-gold mb-3">⭐ Hot Machines (Last 7 Days)</h4>
                        `;
                        
                        machines.forEach(m => {
                            html += `
                                <div class="machine-item" onclick="window.location.href='/machine/${encodeURIComponent(m.machine_name)}'">
                                    <div class="fw-bold text-gold">${m.machine_name.substring(0, 35)}</div>
                                    <div class="d-flex justify-content-between mt-2">
                                        <span>${m.denomination}</span>
                                        <span class="text-success fw-bold">$${m.avg_payout.toLocaleString()}</span>
                                    </div>
                                    <div class="text-muted small mt-1">${m.hits_7d} hits last week • Max: $${m.max_payout.toLocaleString()}</div>
                                </div>
                            `;
                        });
                        
                        content.innerHTML = html;
                        updateTimestamp();
                    });
            }
            
            function updateRegularFloor() {
                fetch('/api/regular-floor-stats')
                    .then(r => r.json())
                    .then(data => {
                        const content = document.getElementById('regular-floor-content');
                        content.querySelector('.loading-overlay').style.display = 'none';
                        
                        const stats = data.stats;
                        const machines = data.machines;
                        const areas = data.areas;
                        
                        let html = `
                            <div class="row mb-3">
                                <div class="col-4 text-center">
                                    <div class="h2 text-gold">${stats.count.toLocaleString()}</div>
                                    <div class="text-muted">Total Hits</div>
                                </div>
                                <div class="col-4 text-center">
                                    <div class="h2 text-gold">$${stats.avg.toLocaleString()}</div>
                                    <div class="text-muted">Avg Payout</div>
                                </div>
                                <div class="col-4 text-center">
                                    <div class="h2 text-success">$${stats.max.toLocaleString()}</div>
                                    <div class="text-muted">Max Hit</div>
                                </div>
                            </div>
                            <hr>
                            <h4 class="text-gold mb-3">⭐ Hot Machines (Last 7 Days)</h4>
                        `;
                        
                        machines.forEach(m => {
                            html += `
                                <div class="machine-item" onclick="window.location.href='/machine/${encodeURIComponent(m.machine_name)}'">
                                    <div class="fw-bold text-gold">${m.machine_name.substring(0, 35)}</div>
                                    <div class="d-flex justify-content-between mt-2">
                                        <span>${m.denomination}</span>
                                        <span class="text-success fw-bold">$${m.avg_payout.toLocaleString()}</span>
                                    </div>
                                    <div class="text-muted small mt-1">${m.hits_7d} hits last week • Max: $${m.max_payout.toLocaleString()}</div>
                                </div>
                            `;
                        });
                        
                        html += `<hr><h4 class="text-gold mb-3">📍 Hot Areas (Last 24h)</h4><div class="row">`;
                        areas.forEach(area => {
                           html += `
                                <div class="col-6 col-md-3 mb-2">
                                    <div class="area-badge w-100 text-center" onclick="window.location.href='/area/${area.area_code}'">
                                        ${area.area_code} • ${area.hits_24h} hits<br>
                                        <small>$${area.avg_payout.toLocaleString()}</small>
                                    </div>
                                </div>
                            `;
                        });
                        html += `</div>`;
                        
                        content.innerHTML = html;
                        updateTimestamp();
                    });
            }
            
            function updateLiveFeed() {
                fetch('/api/live-feed')
                    .then(r => r.json())
                    .then(data => {
                        const content = document.getElementById('live-feed-content');
                        content.querySelector('.loading-overlay').style.display = 'none';
                        
                        let html = '';
                        data.jackpots.forEach(jp => {
                            const amountClass = jp.amount >= 10000 ? 'amount-large' : 
                                              jp.amount >= 5000 ? 'amount-medium' : 'amount-small';
                            
                            html += `
                                <div class="jackpot-feed-item" onclick="window.location.href='/machine/${encodeURIComponent(jp.machine_name)}'">
                                    <div class="row align-items-center">
                                        <div class="col-3">
                                            <div class="${amountClass}">$${jp.amount.toLocaleString()}</div>
                                        </div>
                                        <div class="col-6">
                                            <div class="fw-bold">${jp.machine_name.substring(0, 40)}</div>
                                            <div class="text-muted small">${jp.denomination} • ${jp.location_id || 'Unknown'}</div>
                                        </div>
                                        <div class="col-3 text-end">
                                            <div class="small text-muted">${new Date(jp.hit_timestamp || jp.scraped_at).toLocaleString()}</div>
                                        </div>
                                    </div>
                                </div>
                            `;
                        });
                        
                        content.innerHTML = html;
                        updateTimestamp();
                    });
            }
            
            function updateTimestamp() {
                document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
            }
            
            // Initial load
            updateHighLimit();
            updateRegularFloor();
            updateLiveFeed();
            
            // Set up auto-refresh intervals
            setInterval(updateHighLimit, 120000); // 2 minutes
            setInterval(updateRegularFloor, 120000); // 2 minutes
            setInterval(updateLiveFeed, 30000); // 30 seconds
        </script>
    </body>
    </html>
    """
    
    return render_template_string(template)



@app.route('/zone/<zone_id>')
def zone_detail(zone_id):
    data = get_group_details('zone', zone_id)
    return render_group_report(data, "Zone Analysis")

@app.route('/area/<area_code>')
def area_detail(area_code):
    """Show all jackpots from a specific 2-digit area code"""
    conn = get_db_connection()
    if not conn:
        return "Database error", 500
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get area stats
        cur.execute("""
            SELECT 
                COUNT(*) as total_hits,
                ROUND(AVG(amount), 2) as avg_amount,
                MAX(amount) as max_amount,
                MIN(amount) as min_amount,
                COUNT(*) FILTER (WHERE hit_timestamp > NOW() - INTERVAL '24 hours') as hits_24h,
                COUNT(*) FILTER (WHERE hit_timestamp > NOW() - INTERVAL '7 days') as hits_7d
            FROM jackpots
            WHERE location_id LIKE %s
                AND machine_name NOT ILIKE '%%Poker%%'
                AND machine_name NOT ILIKE '%%Keno%%'
        """, (f"{area_code}%",))
        stats = dict(cur.fetchone() or {})
        
        # Get top machines in this area
        cur.execute("""
            SELECT 
                machine_name,
                denomination,
                COUNT(*) as hit_count,
                ROUND(AVG(amount), 2) as avg_payout,
                MAX(amount) as max_payout,
                MAX(hit_timestamp) as last_hit
            FROM jackpots
            WHERE location_id LIKE %s
                AND machine_name NOT ILIKE '%%Poker%%'
                AND machine_name NOT ILIKE '%%Keno%%'
            GROUP BY machine_name, denomination
            ORDER BY hit_count DESC
            LIMIT 20
        """, (f"{area_code}%",))
        machines = [dict(row) for row in cur.fetchall()]
        
        # Get recent hits from this area
        cur.execute("""
            SELECT 
                machine_name,
                amount,
                denomination,
                location_id,
                hit_timestamp
            FROM jackpots
            WHERE location_id LIKE %s
                AND machine_name NOT ILIKE '%%Poker%%'
                AND machine_name NOT ILIKE '%%Keno%%'
            ORDER BY hit_timestamp DESC NULLS LAST
            LIMIT 50
        """, (f"{area_code}%",))
        recent_hits = [dict(row) for row in cur.fetchall()]
        
        cur.close()
        conn.close()
        
        # Render template
        template = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Area {{ area_code }} Analysis</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
            <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@400;700&family=Lato:wght@300;400;700&display=swap" rel="stylesheet">
            <style>
                :root {
                    --bg-dark: #0f1115;
                    --card-bg: #1a1d23;
                    --text-main: #e0e0e0;
                    --gold: #d4af37;
                    --bronze: #cd7f32;
                    --accent: #00ff9f;
                }
                body {
                    background-color: var(--bg-dark);
                    color: var(--text-main);
                    font-family: 'Lato', sans-serif;
                    padding: 20px;
                }
                .metric-card {
                    background: linear-gradient(145deg, #1a1d23, #22262e);
                    border: 1px solid rgba(212, 175, 55, 0.2);
                    border-radius: 8px;
                    padding: 20px;
                    text-align: center;
                }
                .metric-value { font-family: 'Cinzel', serif; font-size: 1.8em; color: var(--gold); }
                .metric-label { font-size: 0.9em; color: rgba(255,255,255,0.6); margin-top: 5px; }
                h1, h2 { font-family: 'Cinzel', serif; color: var(--gold); }
                .machine-row {
                    background: rgba(26, 29, 35, 0.5);
                    border-left: 3px solid var(--gold);
                    padding: 12px;
                    margin: 8px 0;
                    border-radius: 4px;
                    cursor: pointer;
                    transition: all 0.3s;
                }
                .machine-row:hover {
                    background: rgba(212, 175, 55, 0.1);
                    transform: translateX(5px);
                }
                .back-btn {
                    color: var(--bronze);
                    text-decoration: none;
                    margin-bottom: 20px;
                    display: inline-block;
                }
                .back-btn:hover { color: var(--gold); }
            </style>
        </head>
        <body>
            <div class="container" style="max-width: 1200px;">
                <a href="/" class="back-btn">← Back to Dashboard</a>
                
                <h1>📍 Area {{ area_code }} Analysis</h1>
                <p style="color: rgba(255,255,255,0.6);">Casino floor location code: {{ area_code }}</p>
                
                <!-- Stats -->
                <div class="row g-3 mb-4">
                    <div class="col-6 col-md-3">
                        <div class="metric-card">
                            <div class="metric-value">{{ "{:,}".format(stats.total_hits) if stats.total_hits else '0' }}</div>
                            <div class="metric-label">Total Hits</div>
                        </div>
                    </div>
                    <div class="col-6 col-md-3">
                        <div class="metric-card">
                            <div class="metric-value">${{ "{:,.0f}".format(stats.avg_amount) if stats.avg_amount else '0' }}</div>
                            <div class="metric-label">Avg Payout</div>
                        </div>
                    </div>
                    <div class="col-6 col-md-3">
                        <div class="metric-card">
                            <div class="metric-value">${{ "{:,.0f}".format(stats.max_amount) if stats.max_amount else '0' }}</div>
                            <div class="metric-label">Max Hit</div>
                        </div>
                    </div>
                    <div class="col-6 col-md-3">
                        <div class="metric-card">
                            <div class="metric-value">{{ stats.hits_24h or '0' }}</div>
                            <div class="metric-label">Last 24h</div>
                        </div>
                    </div>
                </div>
                
                <!-- Top Machines -->
                <h2>Top Machines in Area {{ area_code }}</h2>
                <div style="background: var(--card-bg); padding: 20px; border-radius: 8px; margin-bottom: 30px;">
                    {% for machine in machines %}
                    <div class="machine-row" onclick="window.location.href='/machine/{{ machine.machine_name | urlencode }}'">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <div style="font-weight: 700; color: var(--gold);">{{ machine.machine_name[:50] }}</div>
                                <div style="font-size: 0.85em; color: rgba(255,255,255,0.6);">{{ machine.denomination }} • {{ machine.hit_count }} hits</div>
                            </div>
                            <div style="text-align: right;">
                                <div style="font-size: 1.2em; font-weight: 700; color: var(--accent);">${{ "{:,.0f}".format(machine.avg_payout) }}</div>
                                <div style="font-size: 0.8em; color: rgba(255,255,255,0.5);">avg</div>
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                </div>
                
                <!-- Recent Hits -->
                <h2>Recent Jackpots</h2>
                <div style="background: var(--card-bg); padding: 20px; border-radius: 8px;">
                    <div class="table-responsive">
                        <table class="table table-dark table-hover">
                            <thead>
                                <tr>
                                    <th>Machine</th>
                                    <th>Amount</th>
                                    <th>Location</th>
                                    <th>Time</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for hit in recent_hits %}
                                <tr style="cursor: pointer;" onclick="window.location.href='/machine/{{ hit.machine_name | urlencode }}'">
                                    <td>{{ hit.machine_name[:40] }}</td>
                                    <td style="color: var(--accent); font-weight: 700;">${{ "{:,.2f}".format(hit.amount) }}</td>
                                    <td>{{ hit.location_id }}</td>
                                    <td style="color: rgba(255,255,255,0.6);">{{ hit.hit_timestamp.strftime('%m/%d %I:%M %p') if hit.hit_timestamp else 'N/A' }}</td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        return render_template_string(template, area_code=area_code, stats=stats, machines=machines, recent_hits=recent_hits)
        
    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route('/brand/<brand_name>')
def brand_detail(brand_name):
    data = get_group_details('brand', brand_name)
    return render_group_report(data, "Brand Report")

@app.route('/denom/<path:denom_value>')
def denom_detail(denom_value):
    data = get_group_details('denom', denom_value)
    return render_group_report(data, "Bet Size Analysis")

@app.route('/hottest')
@cache.cached(timeout=60)
def hottest_ranking():
    machines = get_all_machine_stats(sort_by='hits', limit=100)
    
    template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Hottest Machines (Frequency)</title>
        {{ styles|safe }}
    </head>
    <body>
        <div class="container">
            <a href="/" style="font-size: 1.1em; margin-bottom: 20px; display: inline-block;">← Back to Treasure Hunter</a>
            
            <h1 class="mb-4 text-center">🔥 Hottest Machines</h1>
            <p class="text-center" style="color: #888; margin-top: -10px; margin-bottom: 30px;">Top 100 Machines by Frequent Hits & Speed</p>
            
            <div class="card p-4">
                <div class="table-responsive">
                    <table class="table table-dark table-hover align-middle">
                        <thead>
                            <tr style="color: var(--text-gold); border-bottom: 2px solid #555;">
                                <th>Rank</th>
                                <th>Machine Name</th>
                                <th>Est. Frequency</th>
                                <th class="text-end">Total Paid Out</th>
                                <th class="text-end">Avg Win</th>
                                <th class="text-end">Hits</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for m in machines %}
                            <tr style="cursor: pointer;" onclick="window.location='/machine/{{ m.machine_name }}'">
                                <td><div class="rank-badge rank-{{ loop.index }}">{{ loop.index }}</div></td>
                                <td>
                                    <div style="font-weight: bold; color: {{ m.color|default('#ffffff') }};">{{ m.machine_name }}</div>
                                    <div style="font-size: 0.8em; color: #666;">{{ m.location_id }}</div>
                                </td>
                                <td style="color: var(--accent); font-weight: bold;">
                                    {% if m.days_per_hit > 0 %}
                                    <span title="Days between hits">Every {{ "%.1f"|format(m.days_per_hit) }} days</span>
                                    {% else %}
                                    <span style="color: #666;">Calculating...</span>
                                    {% endif %}
                                </td>
                                <td class="text-end" style="color: #20c997; font-weight: bold;">${{ "{:,.0f}".format(m.total_payout) }}</td>
                                <td class="text-end" style="color: #ccc;">${{ "{:,.0f}".format(m.avg_payout) }}</td>
                                <td class="text-end"><span style="background: rgba(255, 107, 107, 0.2); color: #ff6b6b; padding: 2px 8px; border-radius: 10px;">{{ "{:,}".format(m.hits) }}</span></td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return render_template_string(template, machines=machines, styles=SHARED_STYLES)

@app.route('/volatility/<tier>')
def volatility_recommendations(tier):
    """Show machine recommendations based on volatility preference"""
    conn = get_db_connection()
    if not conn:
        return "Database error", 500
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Map tier to volatility filter
        if tier == 'low':
            vol_filter = "volatility ILIKE '%Low%'"
            title = "🌿 Steady Play Machines"
            desc = "Low volatility slots for consistent, frequent wins with lower variance"
        elif tier == 'medium':
            vol_filter = "volatility ILIKE '%Medium%'"
            title = "⚖️ Balanced Action Machines"
            desc = "Medium volatility for a mix of small and medium-sized wins"
        elif tier == 'high':
            vol_filter = "volatility ILIKE '%High%'"
            title = "🎆 Big Jackpot Hunters"
            desc = "High volatility machines with potential for massive payouts"
        else:
            return "Invalid tier", 404
        
        # Get machines with this volatility that have jackpot history
        cur.execute(f"""
            SELECT 
                m.machine_name,
                m.manufacturer,
                m.denomination,
                m.volatility,
                COUNT(j.id) as hit_count,
                AVG(j.amount) as avg_payout,
                MAX(j.amount) as max_payout
            FROM slot_machines m
            LEFT JOIN jackpots j ON m.machine_name = j.machine_name
            WHERE {vol_filter}
                AND j.machine_name IS NOT NULL
                AND j.machine_name NOT ILIKE '%Poker%' 
                AND j.machine_name NOT ILIKE '%Keno%'
            GROUP BY m.machine_name, m.manufacturer, m.denomination, m.volatility
            HAVING COUNT(j.id) > 5
            ORDER BY COUNT(j.id) DESC
            LIMIT 50
        """)
        
        machines = cur.fetchall()
        cur.close()
        conn.close()
        
        template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>{{ title }}</title>
            {{ styles|safe }}
        </head>
        <body>
            <div class="container">
                <a href="/" style="font-size: 1.1em; margin-bottom: 20px; display: inline-block;">← Back to Dashboard</a>
                
                <h1 class="mb-2 text-center">{{ title }}</h1>
                <p class="text-center" style="color: #888; margin-bottom: 30px;">{{ desc }}</p>
                
                <div class="card p-4">
                    <div class="table-responsive">
                        <table class="table table-dark table-hover align-middle">
                            <thead>
                                <tr style="color: var(--text-gold); border-bottom: 2px solid #555;">
                                    <th>Machine Name</th>
                                    <th>Manufacturer</th>
                                    <th>Denom</th>
                                    <th>Hit Count</th>
                                    <th>Avg Payout</th>
                                    <th>Max Payout</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for m in machines %}
                                <tr style="cursor: pointer;" onclick="window.location.href='/machine/{{ m.machine_name|urlencode }}'">
                                    <td><strong>{{ m.machine_name }}</strong></td>
                                    <td>{{ m.manufacturer }}</td>
                                    <td>{{ m.denomination }}</td>
                                    <td>{{ "{:,}".format(m.hit_count) }}</td>
                                    <td>${{ "{:,.2f}".format(m.avg_payout) }}</td>
                                    <td>${{ "{:,.2f}".format(m.max_payout) }}</td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        return render_template_string(template, machines=machines, title=title, desc=desc, styles=SHARED_STYLES)
        
    except Exception as e:
        return f"Error: {e}", 500

def render_group_report(data, title_prefix):
    if not data:
        return "Error loading data", 500
        
    template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>{{ title }}: {{ data.value }}</title>
        {{ styles|safe }}
    </head>
    <body>
        <div class="container">
            <a href="/" style="font-size: 1.1em; margin-bottom: 20px; display: inline-block;">← Back to Treasure Hunter</a>
            
            <h1 class="text-center mb-4">{{ title }} <span style="color: #fff;">{{ data.value }}</span></h1>
            
            <div class="row mb-4">
                <div class="col-md-3">
                    <div class="stat-box">
                        <div class="stat-val">{{ "{:,}".format(data.stats.hits) }}</div>
                        <div class="stat-label">Total Jackpots</div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="stat-box">
                        <div class="stat-val">${{ "{:,.2f}".format(data.stats.avg_payout) }}</div>
                        <div class="stat-label">Average Win</div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="stat-box">
                        <div class="stat-val">${{ "{:,.0f}".format(data.stats.max_payout) }}</div>
                        <div class="stat-label">Max Win</div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="stat-box">
                        <div class="stat-val">${{ "{:,.0f}".format(data.stats.total_payout) }}</div>
                        <div class="stat-label">Total Paid Out</div>
                    </div>
                </div>
            </div>
            
            <div class="row">
                <div class="col-md-8">
                    <div class="card">
                        <h3>🏆 Top Performing Machines</h3>
                        <div class="table-responsive">
                            <table class="table table-dark table-hover">
                                <thead>
                                    <tr><th>Machine</th><th>Loc</th><th>Hits</th><th>Avg</th><th>Max</th></tr>
                                </thead>
                                <tbody>
                                    {% for m in data.machines %}
                                    <tr onclick="window.location='/machine/{{ m.machine_name }}'" style="cursor: pointer;">
                                        <td style="color: var(--text-gold); font-weight: bold;">{{ m.machine_name }}</td>
                                        <td>{{ m.location_id }}</td>
                                        <td>{{ "{:,}".format(m.hits) }}</td>
                                        <td style="color: var(--accent);">${{ "{:,.0f}".format(m.avg_payout) }}</td>
                                        <td>${{ "{:,.0f}".format(m.max_payout) }}</td>
                                    </tr>
                                    {% endfor %}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card">
                        <h3>🔥 Recent Activity</h3>
                        {% for hit in data.recent %}
                        <div style="padding: 10px; border-bottom: 1px solid #333;">
                            <div style="font-weight: bold; color: #fff;">${{ "{:,.2f}".format(hit.amount) }}</div>
                            <div style="font-size: 0.8em; color: var(--text-gold);">{{ hit.machine_name }}</div>
                            <div style="font-size: 0.75em; color: #888;">{{ hit.hit_timestamp }}</div>
                        </div>
                        {% endfor %}
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return render_template_string(template, data=data, title=title_prefix, styles=SHARED_STYLES)


@app.route('/transform-data', methods=['GET'])
def transform_data_route():
    """Run data transformation on existing jackpot data"""
    try:
        import subprocess
        result = subprocess.run(
            ['/home/rod/home_ai_stack/venv/bin/python3', 'data_transformer.py'],
            cwd='/home/rod/home_ai_stack',
            capture_output=True,
            text=True,
            timeout=300
        )
        
        return f"<pre>{result.stdout}\n{result.stderr}</pre>"
    except Exception as e:
        return f"Error running transformation: {str(e)}", 500

@app.route('/analytics/machine-performance')
def machine_performance():
    """Machine performance analytics"""
    if not ANALYTICS_AVAILABLE:
        return "Analytics engine not available", 500
    
    try:
        # Get hot machines
        hot_machines = detect_hot_streaks(hours=48, min_hits=2)
        
        # Get top performers by ROI
        conn = get_db_connection()
        if not conn:
            return "Database error", 500
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT DISTINCT machine_name 
            FROM jackpots 
            WHERE hit_timestamp > NOW() - INTERVAL '30 days'
            LIMIT 50
        """)
        machines = [row['machine_name'] for row in cur.fetchall()]
        cur.close()
        conn.close()
        
        # Calculate ROI for top machines
        roi_data = []
        for machine in machines[:20]:
            roi = calculate_machine_roi(machine, days=30)
            if roi:
                roi_data.append(roi)
        
        roi_data.sort(key=lambda x: x['roi_score'], reverse=True)
        
        template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Machine Performance Analytics</title>
            {{ styles|safe }}
        </head>
        <body>
            <div class="container">
                <a href="/" class="back-btn">← Back to Dashboard</a>
                <h1 class="text-center mb-4">🎰 Machine Performance Analytics</h1>
                
                <div class="row">
                    <div class="col-md-6">
                        <div class="card p-4 mb-4">
                            <h3 style="color: var(--gold);">🔥 Hot Machines (48 Hours)</h3>
                            <div class="table-responsive">
                                <table class="table table-dark">
                                    <thead>
                                        <tr>
                                            <th>Location</th>
                                            <th>Machine</th>
                                            <th>Hits</th>
                                            <th>Avg Payout</th>
                                            <th>Heat Score</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {% for m in hot_machines[:10] %}
                                        <tr>
                                            <td><span class="badge bg-secondary">{{ m.location_id }}</span></td>
                                            <td><a href="/machine/{{ m.machine_name|urlencode }}" style="color: var(--gold); text-decoration: none;">{{ m.machine_name[:40] }}</a></td>
                                            <td>{{ m.recent_hits }}</td>
                                            <td style="color: var(--accent);">${{ "{:,.0f}".format(m.avg_payout) }}</td>
                                            <td><span class="badge bg-danger">{{ m.heat_score }}</span></td>
                                        </tr>
                                        {% endfor %}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                    
                    <div class="col-md-6">
                        <div class="card p-4 mb-4">
                            <h3 style="color: var(--gold);">💎 Top ROI Machines (30 Days)</h3>
                            <p style="font-size: 0.85em; color: #888;">ROI = (Frequency × Avg Payout) / 1000</p>
                            <div class="table-responsive">
                                <table class="table table-dark">
                                    <thead>
                                        <tr>
                                            <th>Location</th>
                                            <th>Machine</th>
                                            <th>ROI Score</th>
                                            <th>Hits</th>
                                            <th>Avg</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {% for m in roi_data[:10] %}
                                        <tr>
                                            <td><span class="badge bg-secondary">{{ m.location_id }}</span></td>
                                            <td><a href="/machine/{{ m.machine_name|urlencode }}" style="color: var(--gold); text-decoration: none;">{{ m.machine_name[:40] }}</a></td>
                                            <td><strong style="color: #00ff9f;">{{ m.roi_score }}</strong></td>
                                            <td>{{ m.hit_count }}</td>
                                            <td>${{ "{:,.0f}".format(m.avg_payout) }}</td>
                                        </tr>
                                        {% endfor %}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        return render_template_string(template, hot_machines=hot_machines, 
                                    roi_data=roi_data, styles=SHARED_STYLES)
        
    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route('/analytics/player-patterns')
def player_patterns():
    """Player pattern analytics - temporal analysis"""
    if not ANALYTICS_AVAILABLE:
        return "Analytics engine not available", 500
    
    try:
        # Get hourly patterns
        hourly_data = find_best_playing_times()
        
        # Get weekend vs weekday stats
        conn = get_db_connection()
        if not conn:
            return "Database error", 500
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT 
                is_weekend,
                COUNT(*) as hits,
                AVG(amount) as avg_payout
            FROM jackpots
            WHERE is_weekend IS NOT NULL
            GROUP BY is_weekend
        """)
        weekend_data = list(cur.fetchall())
        
        cur.close()
        conn.close()
        
        template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Player Pattern Analytics</title>
            {{ styles|safe }}
        </head>
        <body>
            <div class="container">
                <a href="/" class="back-btn">← Back to Dashboard</a>
                <h1 class="text-center mb-4">📊 Player Pattern Analytics</h1>
                
                <div class="row">
                    <div class="col-md-8">
                        <div class="card p-4 mb-4">
                            <h3 style="color: var(--gold);">⏰ Best Playing Times (All Time)</h3>
                            <div style="display: grid; grid-template-columns: repeat(6, 1fr); gap: 10px; margin-top: 20px;">
                                {% for hour in hourly_data %}
                                {% set max_hits = hourly_data|map(attribute='hits')|max %}
                                {% set height = (hour.hits / max_hits * 100)|int %}
                                <div style="text-align: center;">
                                    <div style="height: 100px; display: flex; align-items: flex-end; justify-content: center;">
                                        <div style="width: 100%; background: linear-gradient(to top, var(--gold), var(--bronze)); height: {{ height }}%; border-radius: 4px 4px 0 0;"></div>
                                    </div>
                                    <div style="font-size: 0.75em; margin-top: 5px; color: var(--parchment);">{{ hour.display }}</div>
                                    <div style="font-size: 0.7em; color: #888;">{{ hour.hits }} hits</div>
                                </div>
                                {% endfor %}
                            </div>
                        </div>
                    </div>
                    
                    <div class="col-md-4">
                        <div class="card p-4 mb-4">
                            <h3 style="color: var(--gold);">📅 Weekend vs Weekday</h3>
                            {% for wd in weekend_data %}
                            <div style="padding: 15px; margin: 10px 0; background: rgba(212, 175, 55, 0.1); border-left: 3px solid var(--gold);">
                                <h4 style="color: var(--parchment);">{{ 'Weekend' if wd.is_weekend else 'Weekday' }}</h4>
                                <div style="font-size: 1.2em; color: var(--gold);">{{ "{:,}".format(wd.hits) }} hits</div>
                                <div style="color: #888;">Avg: ${{ "{:,.0f}".format(wd.avg_payout) }}</div>
                            </div>
                            {% endfor %}
                        </div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        return render_template_string(template, hourly_data=hourly_data,
                                    weekend_data=weekend_data, styles=SHARED_STYLES)
        
    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route('/analytics/manufacturer-wars')
def manufacturer_wars():
    """Manufacturer comparison analytics"""
    if not ANALYTICS_AVAILABLE:
        return "Analytics engine not available", 500
    
    try:
        manufacturers = analyze_manufacturer_performance()
        
        template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Manufacturer Wars</title>
            {{ styles|safe }}
        </head>
        <body>
            <div class="container">
                <a href="/" class="back-btn">← Back to Dashboard</a>
                <h1 class="text-center mb-4">⚔️ Manufacturer Wars</h1>
                
                <div class="card p-4">
                    <div class="table-responsive">
                        <table class="table table-dark table-hover">
                            <thead>
                                <tr style="color: var(--gold);">
                                    <th>Manufacturer</th>
                                    <th>Market Share</th>
                                    <th>Total Hits</th>
                                    <th>Total Payout</th>
                                    <th>Avg Payout</th>
                                    <th>Max Hit</th>
                                    <th>Machines</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for m in manufacturers %}
                                <tr>
                                    <td><strong>{{ m.manufacturer }}</strong></td>
                                    <td>
                                        <div style="display: flex; align-items: center; gap: 10px;">
                                            <div style="width: 100px; background: rgba(255,255,255,0.1); height: 20px; border-radius: 4px;">
                                                <div style="width: {{ m.market_share }}%; background: var(--gold); height: 100%; border-radius: 4px;"></div>
                                            </div>
                                            <span>{{ m.market_share }}%</span>
                                        </div>
                                    </td>
                                    <td>{{ "{:,}".format(m.total_hits) }}</td>
                                    <td style="color: var(--accent);">${{ "{:,.0f}".format(m.total_payout) }}</td>
                                    <td>${{ "{:,.0f}".format(m.avg_payout) }}</td>
                                    <td>${{ "{:,.0f}".format(m.max_payout) }}</td>
                                    <td>{{ m.unique_machines }}</td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        return render_template_string(template, manufacturers=manufacturers, styles=SHARED_STYLES)
        
    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route('/analytics/game-families')
def game_families():
    """Game family insights"""
    if not ANALYTICS_AVAILABLE:
        return "Analytics engine not available", 500
    
    try:
        families = get_game_family_insights()
        
        template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Game Family Insights</title>
            {{ styles|safe }}
        </head>
        <body>
            <div class="container">
                <a href="/" class="back-btn">← Back to Dashboard</a>
                <h1 class="text-center mb-4">🎮 Game Family Insights</h1>
                
                <div class="card p-4">
                    <div class="table-responsive">
                        <table class="table table-dark table-hover">
                            <thead>
                                <tr style="color: var(--gold);">
                                    <th>Game Family</th>
                                    <th>Total Hits</th>
                                    <th>Avg Payout</th>
                                    <th>Max Payout</th>
                                    <th>Variants</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for f in families %}
                                <tr>
                                    <td><strong>{{ f.game_family }}</strong></td>
                                    <td>{{ "{:,}".format(f.hits) }}</td>
                                    <td style="color: var(--accent);">${{ "{:,.0f}".format(f.avg_payout) }}</td>
                                    <td>${{ "{:,.0f}".format(f.max_payout) }}</td>
                                    <td>{{ f.variants }} versions</td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        return render_template_string(template, families=families, styles=SHARED_STYLES)
        
    except Exception as e:
        return f"Error: {str(e)}", 500


@app.route('/analytics/jvi-rankings')
def jvi_rankings():
    """JVI (Jackpot Value Index) rankings - ML-enhanced balanced machine scoring"""
    if not ANALYTICS_AVAILABLE:
        return "Analytics engine not available", 500
    
    try:
        # Import ML module
        import sys
        sys.path.insert(0, '/home/rod/home_ai_stack')
        from jvi_ml import get_ml_enhanced_rankings, load_models
        
        # Load ML models
        load_models()
        
        # Get ML-enhanced rankings for each mode
        jvi_balanced = get_ml_enhanced_rankings(limit=20, sort_by='balanced')
        jvi_big = get_ml_enhanced_rankings(limit=20, sort_by='big')
        jvi_fast = get_ml_enhanced_rankings(limit=20, sort_by='fast')
        
        # Get per-denomination stats
        conn = get_db_connection()
        if conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("""
                SELECT 
                    normalized_denomination as denom,
                    COUNT(*) as hits,
                    AVG(amount) as avg_payout,
                    MAX(amount) as max_payout
                FROM jackpots
                WHERE normalized_denomination IS NOT NULL
                    AND amount IS NOT NULL
                GROUP BY normalized_denomination
                ORDER BY hits DESC
                LIMIT 15
            """)
            denom_stats = list(cur.fetchall())
            cur.close()
            conn.close()
        else:
            denom_stats = []
        
        template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>ML-Enhanced JVI Rankings</title>
            {{ styles|safe }}
            <style>
                .cluster-badge {
                    display: inline-block;
                    padding: 3px 8px;
                    border-radius: 4px;
                    font-size: 0.75em;
                    font-weight: bold;
                    margin-left: 5px;
                }
                .cluster-big { background: #ff6b6b; color: white; }
                .cluster-fast { background: #4dabf7; color: white; }
                .cluster-balanced { background: #ffd43b; color: #333; }
                .growth-positive { color: #00ff9f; }
                .growth-negative { color: #ff6b6b; }
            </style>
        </head>
        <body>
            <div class="container">
                <a href="/" class="back-btn">← Back to Dashboard</a>
                <h1 class="text-center mb-4">🤖 ML-Enhanced JVI Rankings</h1>
                <p class="text-center" style="color: #888; margin-bottom: 10px;">Machine Learning predictions with behavioral clustering</p>
                <p class="text-center" style="color: #666; font-size: 0.9em; margin-bottom: 30px;">Model trained on 278 machines • R² Score: 0.971</p>
                
                <div class="row mb-4">
                    <div class="col-md-4">
                        <div class="card p-3">
                            <h3 style="color: var(--gold);">⚖️ Balanced JVI</h3>
                            <p style="font-size: 0.8em; color: #888;">Frequency × Avg × Recency</p>
                            <div class="table-responsive">
                                <table class="table table-dark table-sm">
                                    <thead>
                                        <tr>
                                            <th>Machine</th>
                                            <th>JVI</th>
                                            <th>Predicted</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {% for m in jvi_balanced[:10] %}
                                        <tr>
                                            <td style="font-size: 0.85em;">
                                                <strong style="color: var(--gold);">#{{ m.bank }}</strong> - 
                                                {{ m.machine_name[:25] }}
                                                <span class="cluster-badge cluster-{{ m.ml_cluster.lower().replace(' ', '-') }}">
                                                    {{ m.ml_cluster }}
                                                </span>
                                            </td>
                                            <td><strong style="color: #00ff9f;">{{ m.jvi_balanced }}</strong></td>
                                            <td>
                                                {{ m.predicted_jvi }}
                                                <span class="{% if m.jvi_growth > 0 %}growth-positive{% else %}growth-negative{% endif %}" style="font-size: 0.8em;">
                                                    ({{ "+" if m.jvi_growth > 0 else "" }}{{ m.jvi_growth }})
                                                </span>
                                            </td>
                                        </tr>
                                        {% endfor %}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                    
                    <div class="col-md-4">
                        <div class="card p-3">
                            <h3 style="color: #ff6b6b;">💰 Big Payout JVI</h3>
                            <p style="font-size: 0.8em; color: #888;">Frequency × Max Payout</p>
                            <div class="table-responsive">
                                <table class="table table-dark table-sm">
                                    <thead>
                                        <tr>
                                            <th>Machine</th>
                                            <th>JVI</th>
                                            <th>Max</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {% for m in jvi_big[:10] %}
                                        <tr>
                                            <td style="font-size: 0.85em;">
                                                <strong style="color: var(--gold);">#{{ m.bank }}</strong> - {{ m.machine_name[:20] }}
                                                <span class="cluster-badge cluster-{{ m.ml_cluster.lower().replace(' ', '-') }}">
                                                    {{ m.ml_cluster }}
                                                </span>
                                            </td>
                                            <td><strong style="color: #ff6b6b;">{{ m.jvi_big }}</strong></td>
                                            <td>${{ "{:,.0f}".format(m.max_jackpot) }}</td>
                                        </tr>
                                        {% endfor %}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                    
                    <div class="col-md-4">
                        <div class="card p-3">
                            <h3 style="color: #20c997;">⚡ Fast Hitter JVI</h3>
                            <p style="font-size: 0.8em; color: #888;">Frequency² × Avg</p>
                            <div class="table-responsive">
                                <table class="table table-dark table-sm">
                                    <thead>
                                        <tr>
                                            <th>Machine</th>
                                            <th>JVI</th>
                                            <th>Hits</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {% for m in jvi_fast[:10] %}
                                        <tr>
                                            <td style="font-size: 0.85em;">
                                                <strong style="color: var(--gold);">#{{ m.bank }}</strong> - 
                                                {{ m.machine_name[:20] }}
                                                <span class="cluster-badge cluster-{{ m.ml_cluster.lower().replace(' ', '-') }}">
                                                    {{ m.ml_cluster }}
                                                </span>
                                            </td>
                                            <td><strong style="color: #20c997;">{{ m.jvi_fast }}</strong></td>
                                            <td>{{ m.hits }}</td>
                                        </tr>
                                        {% endfor %}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="card p-4 mb-4">
                    <h3 style="color: var(--gold);">🎯 ML Cluster Insights</h3>
                    <div class="row">
                        <div class="col-md-4">
                            <div style="padding: 15px; background: rgba(255, 107, 107, 0.1); border-left: 4px solid #ff6b6b;">
                                <h4 style="color: #ff6b6b;">Big Wins Cluster</h4>
                                <p style="font-size: 0.9em; color: #aaa;">Machines with high total payouts and large jackpots. Best for chasing big wins.</p>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div style="padding: 15px; background: rgba(77, 171, 247, 0.1); border-left: 4px solid #4dabf7;">
                                <h4 style="color: #4dabf7;">Fast Cycle Cluster</h4>
                                <p style="font-size: 0.9em; color: #aaa;">Frequent hitters with short gaps between jackpots. Best for consistent action.</p>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div style="padding: 15px; background: rgba(255, 212, 59, 0.1); border-left: 4px solid #ffd43b;">
                                <h4 style="color: #ffd43b;">Balanced Cluster</h4>
                                <p style="font-size: 0.9em; color: #aaa;">Well-rounded machines with good frequency and payout balance.</p>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="card p-4">
                    <h3 style="color: var(--gold);">📊 Performance by Denomination</h3>
                    <div class="table-responsive">
                        <table class="table table-dark table-hover">
                            <thead>
                                <tr style="color: var(--gold);">
                                    <th>Denomination</th>
                                    <th>Total Hits</th>
                                    <th>Avg Payout</th>
                                    <th>Max Payout</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for d in denom_stats %}
                                <tr>
                                    <td><strong>{{ d.denom }}</strong></td>
                                    <td>{{ "{:,}".format(d.hits) }}</td>
                                    <td style="color: var(--accent);">${{ "{:,.2f}".format(d.avg_payout) }}</td>
                                    <td>${{ "{:,.2f}".format(d.max_payout) }}</td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        return render_template_string(template, jvi_balanced=jvi_balanced, jvi_big=jvi_big,
                                    jvi_fast=jvi_fast, denom_stats=denom_stats, styles=SHARED_STYLES)
        
    except Exception as e:
        return f"Error: {str(e)}<br><br>Make sure jvi_ml.py is deployed and models are trained.", 500

    """JVI (Jackpot Value Index) rankings - balanced machine scoring"""
    if not ANALYTICS_AVAILABLE:
        return "Analytics engine not available", 500
    
    try:
        conn = get_db_connection()
        if not conn:
            return "Database error", 500
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get top machines by each JVI mode
        cur.execute("""
            SELECT DISTINCT machine_name, normalized_denomination
            FROM jackpots
            WHERE hit_timestamp > NOW() - INTERVAL '30 days'
                AND amount IS NOT NULL
            LIMIT 100
        """)
        machines = cur.fetchall()
        
        # Calculate JVI for each mode
        jvi_balanced = []
        jvi_big = []
        jvi_fast = []
        
        for machine in machines[:30]:  # Limit to avoid timeout
            for mode, target_list in [('balanced', jvi_balanced), ('big', jvi_big), ('fast', jvi_fast)]:
                jvi = calculate_jvi(machine['machine_name'], days=30, mode=mode)
                if jvi and jvi['jvi'] > 0:
                    jvi['denomination'] = machine.get('normalized_denomination', 'Unknown')
                    target_list.append(jvi)
        
        # Sort by JVI score
        jvi_balanced.sort(key=lambda x: x['jvi'], reverse=True)
        jvi_big.sort(key=lambda x: x['jvi'], reverse=True)
        jvi_fast.sort(key=lambda x: x['jvi'], reverse=True)
        
        # Get per-denomination stats
        cur.execute("""
            SELECT 
                normalized_denomination as denom,
                COUNT(*) as hits,
                AVG(amount) as avg_payout,
                MAX(amount) as max_payout
            FROM jackpots
            WHERE normalized_denomination IS NOT NULL
                AND amount IS NOT NULL
            GROUP BY normalized_denomination
            ORDER BY hits DESC
            LIMIT 15
        """)
        denom_stats = list(cur.fetchall())
        
        cur.close()
        conn.close()
        
        template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>JVI Rankings</title>
            {{ styles|safe }}
        </head>
        <body>
            <div class="container">
                <a href="/" class="back-btn">← Back to Dashboard</a>
                <h1 class="text-center mb-4">💎 JVI Rankings</h1>
                <p class="text-center" style="color: #888; margin-bottom: 30px;">Jackpot Value Index - Balanced machine scoring across multiple metrics</p>
                
                <div class="row mb-4">
                    <div class="col-md-4">
                        <div class="card p-3">
                            <h3 style="color: var(--gold);">⚖️ Balanced JVI</h3>
                            <p style="font-size: 0.8em; color: #888;">Frequency × Avg × Recency</p>
                            <div class="table-responsive">
                                <table class="table table-dark table-sm">
                                    <thead>
                                        <tr>
                                            <th>Machine</th>
                                            <th>JVI</th>
                                            <th>Hits</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {% for m in jvi_balanced[:10] %}
                                        <tr>
                                            <td style="font-size: 0.85em;">{{ m.machine_name[:30] }}</td>
                                            <td><strong style="color: #00ff9f;">{{ m.jvi }}</strong></td>
                                            <td>{{ m.hit_count }}</td>
                                        </tr>
                                        {% endfor %}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                    
                    <div class="col-md-4">
                        <div class="card p-3">
                            <h3 style="color: #ff6b6b;">💰 Big Payout JVI</h3>
                            <p style="font-size: 0.8em; color: #888;">Frequency × Max Payout</p>
                            <div class="table-responsive">
                                <table class="table table-dark table-sm">
                                    <thead>
                                        <tr>
                                            <th>Machine</th>
                                            <th>JVI</th>
                                            <th>Max</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {% for m in jvi_big[:10] %}
                                        <tr>
                                            <td style="font-size: 0.85em;">{{ m.machine_name[:30] }}</td>
                                            <td><strong style="color: #ff6b6b;">{{ m.jvi }}</strong></td>
                                            <td>${{ "{:,.0f}".format(m.max_payout) }}</td>
                                        </tr>
                                        {% endfor %}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                    
                    <div class="col-md-4">
                        <div class="card p-3">
                            <h3 style="color: #20c997;">⚡ Fast Hitter JVI</h3>
                            <p style="font-size: 0.8em; color: #888;">Frequency² × Avg</p>
                            <div class="table-responsive">
                                <table class="table table-dark table-sm">
                                    <thead>
                                        <tr>
                                            <th>Machine</th>
                                            <th>JVI</th>
                                            <th>Hits</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {% for m in jvi_fast[:10] %}
                                        <tr>
                                            <td style="font-size: 0.85em;">{{ m.machine_name[:30] }}</td>
                                            <td><strong style="color: #20c997;">{{ m.jvi }}</strong></td>
                                            <td>{{ m.hit_count }}</td>
                                        </tr>
                                        {% endfor %}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="card p-4">
                    <h3 style="color: var(--gold);">📊 Performance by Denomination</h3>
                    <div class="table-responsive">
                        <table class="table table-dark table-hover">
                            <thead>
                                <tr style="color: var(--gold);">
                                    <th>Denomination</th>
                                    <th>Total Hits</th>
                                    <th>Avg Payout</th>
                                    <th>Max Payout</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for d in denom_stats %}
                                <tr>
                                    <td><strong>{{ d.denom }}</strong></td>
                                    <td>{{ "{:,}".format(d.hits) }}</td>
                                    <td style="color: var(--accent);">${{ "{:,.2f}".format(d.avg_payout) }}</td>
                                    <td>${{ "{:,.2f}".format(d.max_payout) }}</td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        return render_template_string(template, jvi_balanced=jvi_balanced, jvi_big=jvi_big,
                                    jvi_fast=jvi_fast, denom_stats=denom_stats, styles=SHARED_STYLES)
        
    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route('/analytics/cluster-visualization')
@cache.cached(timeout=300)
def cluster_visualization():
    """Interactive cluster visualization with Plotly.js"""
    if not ANALYTICS_AVAILABLE:
        return "Analytics engine not available", 500
    
    try:
        # Import ML module
        import sys
        sys.path.insert(0, '/home/rod/home_ai_stack')
        from jvi_ml import get_ml_enhanced_rankings, load_models
        
        # Load ML models
        load_models()
        
        # Get ML-enhanced rankings
        rankings = get_ml_enhanced_rankings(limit=100, sort_by='balanced')
        
        template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Cluster Visualization</title>
            {{ styles|safe }}
            <script src="https://cdn.plot.ly/plotly-2.35.0.min.js"></script>
            <style>
                .viz-container {
                    background: rgba(26, 26, 26, 0.95);
                    padding: 20px;
                    border-radius: 8px;
                    margin: 20px 0;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <a href="/" class="back-btn">← Back to Dashboard</a>
                <h1 class="text-center mb-4">🎯 ML Cluster Visualization</h1>
                <p class="text-center" style="color: #888; margin-bottom: 30px;">
                    Interactive scatter plot showing {{ rankings|length }} machines clustered by behavior patterns
                </p>
                
                <div class="viz-container">
                    <div id="scatter" style="width: 100%; height: 600px;"></div>
                </div>
                
                <div class="viz-container mt-4">
                    <h3 style="color: var(--gold); margin-bottom: 20px;">📊 JVI Distribution</h3>
                    <div id="histogram" style="width: 100%; height: 400px;"></div>
                </div>
                
                <div class="card p-4 mt-4">
                    <h3 style="color: var(--gold);">📊 Cluster Legend</h3>
                    <div class="row">
                        <div class="col-md-3">
                            <div style="padding: 15px; background: rgba(255, 107, 107, 0.1); border-left: 4px solid #ff6b6b;">
                                <h4 style="color: #ff6b6b;">💰 Big Wins</h4>
                                <p style="font-size: 0.9em; color: #aaa;">High total payout + high avg jackpot</p>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div style="padding: 15px; background: rgba(77, 171, 247, 0.1); border-left: 4px solid #4dabf7;">
                                <h4 style="color: #4dabf7;">🔥 Fast Cycle</h4>
                                <p style="font-size: 0.9em; color: #aaa;">High hit rate + low hours between hits</p>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div style="padding: 15px; background: rgba(32, 201, 151, 0.1); border-left: 4px solid #20c997;">
                                <h4 style="color: #20c997;">📈 High Volume</h4>
                                <p style="font-size: 0.9em; color: #aaa;">High hit count, consistent activity</p>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div style="padding: 15px; background: rgba(212, 175, 55, 0.1); border-left: 4px solid #d4af37;">
                                <h4 style="color: #d4af37;">⚖️ Balanced</h4>
                                <p style="font-size: 0.9em; color: #aaa;">Well-rounded across all metrics</p>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="card p-4 mt-4">
                    <h3 style="color: var(--gold);">💡 How to Read This Chart</h3>
                    <ul style="color: #aaa;">
                        <li><strong>X-Axis (Payout Volume):</strong> Normalized total payout - further right = higher total winnings</li>
                        <li><strong>Y-Axis (Hit Frequency):</strong> Normalized hit rate - higher up = more frequent jackpots</li>
                        <li><strong>Bubble Size:</strong> Average jackpot amount - larger bubbles = bigger average wins</li>
                        <li><strong>Color:</strong> ML cluster assignment based on behavior patterns</li>
                        <li><strong>Hover:</strong> See machine name, denomination, JVI scores, and predictions</li>
                    </ul>
                </div>
            </div>
            
            <script>
            const data = {{ rankings|tojson }};
            const traces = {};
            
            const clusterColors = {
                'Big Wins': 'rgb(255,107,107)',
                'Fast Cycle': 'rgb(77,171,247)',
                'High Volume': 'rgb(32,201,151)',
                'Balanced': 'rgb(212,175,55)'
            };
            
            data.forEach(m => {
                const cluster = m.ml_cluster || 'Balanced';
                
                if (!traces[cluster]) {
                    traces[cluster] = {
                        x: [],
                        y: [],
                        mode: 'markers',
                        name: cluster,
                        marker: {
                            size: [],
                            color: clusterColors[cluster] || 'gray',
                            opacity: 0.7,
                            line: {
                                color: 'white',
                                width: 1
                            }
                        },
                        text: [],
                        hovertemplate: '<b>%{text}</b><br>' +
                                     'Location: %{customdata[3]}<br>' +
                                     'Payout Volume: %{x:.1f}<br>' +
                                     'Hit Frequency: %{y:.1f}<br>' +
                                     'JVI: %{customdata[0]}<br>' +
                                     'Predicted: %{customdata[1]}<br>' +
                                     'Growth: %{customdata[2]}<extra></extra>',
                        customdata: []
                    };
                }
                
                const trace = traces[cluster];
                trace.x.push((m.n_total || 0) * 100);  // Normalized total payout
                trace.y.push((m.n_rate || 0) * 100);   // Normalized hit rate
                trace.marker.size.push(Math.max(8, Math.sqrt((m.avg_jackpot || 100) / 10)));
                trace.text.push('#' + (m.bank || 'N/A') + ' - ' + m.machine_name + ' (' + (m.denomination || 'N/A') + ')');
                trace.customdata.push([
                    m.jvi_balanced || 0,
                    m.predicted_jvi || 0,
                    m.jvi_growth || 0,
                    '#' + (m.bank || 'N/A')
                ]);
            });
            
            const layout = {
                title: {
                    text: 'JVI Machine Clusters - Behavioral Analysis',
                    font: { color: '#d4af37', size: 20 }
                },
                xaxis: {
                    title: 'Payout Volume (normalized %)',
                    gridcolor: 'rgba(255,255,255,0.1)',
                    color: '#aaa'
                },
                yaxis: {
                    title: 'Hit Frequency (normalized %)',
                    gridcolor: 'rgba(255,255,255,0.1)',
                    color: '#aaa'
                },
                hovermode: 'closest',
                plot_bgcolor: 'rgba(26,26,26,0.5)',
                paper_bgcolor: 'rgba(26,26,26,0.5)',
                font: { color: '#f4e8d0' },
                legend: {
                    bgcolor: 'rgba(26,26,26,0.8)',
                    bordercolor: '#d4af37',
                    borderwidth: 1
                }
            };
            
            const config = {
                responsive: true,
                displayModeBar: true,
                modeBarButtonsToRemove: ['lasso2d', 'select2d']
            };
            
            Plotly.newPlot('scatter', Object.values(traces), layout, config);
            
            // JVI Distribution Histogram
            const jviValues = data.map(m => m.jvi_balanced || 0);
            const histogramTrace = {
                x: jviValues,
                type: 'histogram',
                nbinsx: 20,
                marker: {
                    color: '#d4af37',
                    opacity: 0.7,
                    line: {
                        color: '#fff',
                        width: 1
                    }
                },
                name: 'JVI Distribution'
            };
            
            const histogramLayout = {
                title: {
                    text: 'JVI Score Distribution',
                    font: { color: '#d4af37', size: 18 }
                },
                xaxis: {
                    title: 'JVI Score',
                    gridcolor: 'rgba(255,255,255,0.1)',
                    color: '#aaa'
                },
                yaxis: {
                    title: 'Number of Machines',
                    gridcolor: 'rgba(255,255,255,0.1)',
                    color: '#aaa'
                },
                plot_bgcolor: 'rgba(26,26,26,0.5)',
                paper_bgcolor: 'rgba(26,26,26,0.5)',
                font: { color: '#f4e8d0' },
                bargap: 0.05
            };
            
            Plotly.newPlot('histogram', [histogramTrace], histogramLayout, config);
            </script>
        </body>
        </html>
        """
        
        return render_template_string(template, rankings=rankings, styles=SHARED_STYLES)
        
    except Exception as e:
        return f"Error: {str(e)}<br><br>Make sure jvi_ml.py is deployed and models are trained.", 500

@app.route('/retrain-jvi', methods=['GET', 'POST'])
def retrain_jvi():
    """Manually retrain the JVI ML model"""
    try:
        import sys
        sys.path.insert(0, '/home/rod/home_ai_stack')
        from jvi_ml import train_jvi_model, load_models
        
        if request.method == 'POST':
            # Perform retraining
            import time
            start_time = time.time()
            
            success = train_jvi_model()
            training_time = time.time() - start_time
            
            if success:
                # Reload models
                load_models()
                
                return f"""
                <html>
                <head>
                    <title>Model Retrained</title>
                    <style>
                        body {{ background: #1a1a1a; color: #f4e8d0; font-family: Arial; padding: 40px; }}
                        .success {{ background: rgba(0, 255, 159, 0.1); border: 2px solid #00ff9f; padding: 20px; border-radius: 8px; }}
                        .metric {{ margin: 10px 0; padding: 10px; background: rgba(255,255,255,0.05); }}
                        a {{ color: #00ff9f; text-decoration: none; }}
                    </style>
                </head>
                <body>
                    <div class="success">
                        <h1>✅ Model Retrained Successfully!</h1>
                        <div class="metric"><strong>Training Time:</strong> {training_time:.2f} seconds</div>
                        <div class="metric"><strong>Status:</strong> Model loaded and ready</div>
                        <p style="margin-top: 20px;">
                            <a href="/analytics/jvi-rankings">→ View JVI Rankings</a> | 
                            <a href="/">→ Back to Dashboard</a>
                        </p>
                    </div>
                </body>
                </html>
                """
            else:
                return "❌ Model retraining failed. Check logs for details.", 500
        
        # GET request - show confirmation page
        template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Retrain JVI Model</title>
            {{ styles|safe }}
        </head>
        <body>
            <div class="container">
                <a href="/" class="back-btn">← Back to Dashboard</a>
                <h1 class="text-center mb-4">🔄 Retrain JVI Model</h1>
                
                <div class="card p-4">
                    <h3 style="color: var(--gold);">Model Retraining</h3>
                    <p style="color: #aaa; margin: 20px 0;">
                        This will retrain the machine learning model using the latest jackpot data.
                        The process typically takes 10-30 seconds depending on data volume.
                    </p>
                    
                    <div style="background: rgba(255, 193, 7, 0.1); border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0;">
                        <h4 style="color: #ffc107; margin-top: 0;">⚠️ Important</h4>
                        <ul style="color: #aaa; margin: 10px 0;">
                            <li>Retraining will use all available jackpot data</li>
                            <li>The current model will be backed up automatically</li>
                            <li>Analytics will be briefly unavailable during training</li>
                        </ul>
                    </div>
                    
                    <form method="POST" style="margin-top: 30px;">
                        <button type="submit" style="background: var(--gold); color: #000; border: none; padding: 15px 30px; font-size: 1.1em; border-radius: 4px; cursor: pointer; font-weight: bold;">
                            🚀 Start Retraining
                        </button>
                    </form>
                </div>
            </div>
        </body>
        </html>
        """
        
        return render_template_string(template, styles=SHARED_STYLES)
        
    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route('/analytics/cluster-trends')
def cluster_trends():
    """Track cluster membership changes over time"""
    try:
        conn = get_db_connection()
        if not conn:
            return "Database error", 500
        
        # Get cluster history
        df = pd.read_sql("""
            SELECT 
                snapshot_date,
                cluster_label,
                COUNT(*) as machine_count,
                AVG(jvi_score) as avg_jvi
            FROM cluster_history
            WHERE snapshot_date > CURRENT_DATE - INTERVAL '90 days'
            GROUP BY snapshot_date, cluster_label
            ORDER BY snapshot_date, cluster_label
        """, conn)
        conn.close()
        
        if df.empty:
            return "No cluster history data yet. Run a snapshot first.", 400
        
        # Prepare data for Plotly
        clusters = df['cluster_label'].unique()
        cluster_colors = {
            'Big Wins': '#ff6b6b',
            'Fast Cycle': '#4dabf7',
            'High Volume': '#20c997',
            'Balanced': '#d4af37'
        }
        
        traces = []
        for cluster in clusters:
            cluster_data = df[df['cluster_label'] == cluster]
            traces.append({
                'x': cluster_data['snapshot_date'].dt.strftime('%Y-%m-%d').tolist(),
                'y': cluster_data['machine_count'].tolist(),
                'mode': 'lines+markers',
                'name': cluster,
                'line': {'color': cluster_colors.get(cluster, '#888'), 'width': 3},
                'marker': {'size': 8}
            })
        
        template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Cluster Trends</title>
            {{ styles|safe }}
            <script src="https://cdn.plot.ly/plotly-2.35.0.min.js"></script>
        </head>
        <body>
            <div class="container">
                <a href="/" class="back-btn">← Back to Dashboard</a>
                <h1 class="text-center mb-4">📈 Cluster Trends Over Time</h1>
                <p class="text-center" style="color: #888; margin-bottom: 30px;">
                    Track how machines move between clusters over time
                </p>
                
                <div style="background: rgba(26, 26, 26, 0.95); padding: 20px; border-radius: 8px;">
                    <div id="trends-chart" style="width: 100%; height: 600px;"></div>
                </div>
                
                <div class="card p-4 mt-4">
                    <h3 style="color: var(--gold);">💡 Understanding Cluster Trends</h3>
                    <ul style="color: #aaa;">
                        <li><strong>Rising Lines:</strong> More machines joining this cluster</li>
                        <li><strong>Falling Lines:</strong> Machines moving to other clusters</li>
                        <li><strong>Stable Lines:</strong> Consistent cluster membership</li>
                        <li><strong>Snapshots:</strong> Taken weekly to track changes</li>
                    </ul>
                    
                    <form method="POST" action="/analytics/save-cluster-snapshot" style="margin-top: 20px;">
                        <button type="submit" class="btn" style="background: var(--gold); color: #000; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer;">
                            📸 Save Current Snapshot
                        </button>
                    </form>
                </div>
            </div>
            
            <script>
            const traces = {{ traces|tojson }};
            
            const layout = {
                title: {
                    text: 'Cluster Membership Over Time',
                    font: { color: '#d4af37', size: 20 }
                },
                xaxis: {
                    title: 'Date',
                    gridcolor: 'rgba(255,255,255,0.1)',
                    color: '#aaa'
                },
                yaxis: {
                    title: 'Number of Machines',
                    gridcolor: 'rgba(255,255,255,0.1)',
                    color: '#aaa'
                },
                plot_bgcolor: 'rgba(26,26,26,0.5)',
                paper_bgcolor: 'rgba(26,26,26,0.5)',
                font: { color: '#f4e8d0' },
                legend: { bgcolor: 'rgba(26,26,26,0.8)' },
                hovermode: 'x unified'
            };
            
            Plotly.newPlot('trends-chart', traces, layout, {responsive: true});
            </script>
        </body>
        </html>
        """
        
        return render_template_string(template, traces=traces, styles=SHARED_STYLES)
        
    except Exception as e:
        import traceback
        return f"Cluster trends error: {str(e)}<br><pre>{traceback.format_exc()}</pre>", 500

@app.route('/analytics/save-cluster-snapshot', methods=['POST'])
def save_cluster_snapshot():
    """Save current cluster assignments to history"""
    try:
        import sys
        sys.path.insert(0, '/home/rod/home_ai_stack')
        from jvi_ml import get_ml_enhanced_rankings, load_models
        
        load_models()
        rankings = get_ml_enhanced_rankings(limit=500, sort_by='balanced')
        
        conn = get_db_connection()
        if not conn:
            return "Database error", 500
        
        cur = conn.cursor()
        
        # Insert snapshot
        for r in rankings:
            cur.execute("""
                INSERT INTO cluster_history (machine_name, cluster_label, jvi_score, snapshot_date)
                VALUES (%s, %s, %s, CURRENT_DATE)
                ON CONFLICT DO NOTHING
            """, (r['machine_name'], r.get('ml_cluster', 'Balanced'), r.get('jvi_balanced', 0)))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return f"""
        <html>
        <head>
            <title>Snapshot Saved</title>
            <style>
                body {{ background: #1a1a1a; color: #f4e8d0; font-family: Arial; padding: 40px; }}
                .success {{ background: rgba(0, 255, 159, 0.1); border: 2px solid #00ff9f; padding: 20px; border-radius: 8px; }}
                a {{ color: #00ff9f; text-decoration: none; }}
            </style>
        </head>
        <body>
            <div class="success">
                <h1>✅ Cluster Snapshot Saved!</h1>
                <p><strong>Machines Saved:</strong> {len(rankings)}</p>
                <p><strong>Date:</strong> {datetime.now().strftime('%Y-%m-%d')}</p>
                <p style="margin-top: 20px;">
                    <a href="/analytics/cluster-trends">→ View Cluster Trends</a> | 
                    <a href="/">→ Back to Dashboard</a>
                </p>
            </div>
        </body>
        </html>
        """
        
    except Exception as e:
        import traceback
        return f"Snapshot error: {str(e)}<br><pre>{traceback.format_exc()}</pre>", 500

@app.route('/analytics/jackpot-forecast')
def jackpot_forecast():
    """30-day jackpot forecast using Prophet"""
    try:
        from prophet import Prophet
        import json
        
        conn = get_db_connection()
        if not conn:
            return "Database error", 500
        
        # Get daily jackpot counts
        df = pd.read_sql("""
            SELECT DATE(hit_timestamp) as ds, COUNT(*) as y, SUM(amount) as payout
            FROM jackpots
            WHERE hit_timestamp > NOW() - INTERVAL '180 days'
            GROUP BY DATE(hit_timestamp)
            ORDER BY ds
        """, conn)
        conn.close()
        
        if len(df) < 30:
            return "Insufficient data for forecasting (need 30+ days)", 400
        
        # Train Prophet model
        m = Prophet(yearly_seasonality=True, weekly_seasonality=True, daily_seasonality=False)
        m.add_seasonality(name='monthly', period=30.5, fourier_order=5)
        m.fit(df[['ds', 'y']])
        
        # Make 30-day forecast
        future = m.make_future_dataframe(periods=30)
        forecast = m.predict(future)
        
        # Prepare data for Plotly
        forecast_data = {
            'dates': forecast['ds'].dt.strftime('%Y-%m-%d').tolist(),
            'predicted': forecast['yhat'].tolist(),
            'lower': forecast['yhat_lower'].tolist(),
            'upper': forecast['yhat_upper'].tolist(),
            'actual': df['y'].tolist() + [None] * 30
        }
        
        template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Jackpot Forecast</title>
            {{ styles|safe }}
            <script src="https://cdn.plot.ly/plotly-2.35.0.min.js"></script>
        </head>
        <body>
            <div class="container">
                <a href="/" class="back-btn">← Back to Dashboard</a>
                <h1 class="text-center mb-4">📈 30-Day Jackpot Forecast</h1>
                <p class="text-center" style="color: #888; margin-bottom: 30px;">
                    Powered by Facebook Prophet - Time Series Forecasting
                </p>
                
                <div style="background: rgba(26, 26, 26, 0.95); padding: 20px; border-radius: 8px;">
                    <div id="forecast-chart" style="width: 100%; height: 600px;"></div>
                </div>
                
                <div class="card p-4 mt-4">
                    <h3 style="color: var(--gold);">📊 Forecast Insights</h3>
                    <ul style="color: #aaa;">
                        <li><strong>Blue Line:</strong> Predicted daily jackpot count</li>
                        <li><strong>Shaded Area:</strong> 95% confidence interval</li>
                        <li><strong>Black Dots:</strong> Historical actual data</li>
                        <li><strong>Seasonality:</strong> Weekly and monthly patterns detected</li>
                    </ul>
                </div>
            </div>
            
            <script>
            const data = {{ forecast_data|tojson }};
            
            const traces = [
                {
                    x: data.dates,
                    y: data.predicted,
                    mode: 'lines',
                    name: 'Forecast',
                    line: { color: '#4dabf7', width: 3 }
                },
                {
                    x: data.dates,
                    y: data.upper,
                    mode: 'lines',
                    name: 'Upper Bound',
                    line: { width: 0 },
                    showlegend: false
                },
                {
                    x: data.dates,
                    y: data.lower,
                    mode: 'lines',
                    name: 'Lower Bound',
                    fill: 'tonexty',
                    fillcolor: 'rgba(77, 171, 247, 0.2)',
                    line: { width: 0 },
                    showlegend: false
                },
                {
                    x: data.dates.slice(0, data.actual.filter(x => x !== null).length),
                    y: data.actual.filter(x => x !== null),
                    mode: 'markers',
                    name: 'Actual',
                    marker: { color: '#000', size: 6 }
                }
            ];
            
            const layout = {
                title: {
                    text: 'Daily Jackpot Count Forecast',
                    font: { color: '#d4af37', size: 20 }
                },
                xaxis: {
                    title: 'Date',
                    gridcolor: 'rgba(255,255,255,0.1)',
                    color: '#aaa'
                },
                yaxis: {
                    title: 'Jackpot Count',
                    gridcolor: 'rgba(255,255,255,0.1)',
                    color: '#aaa'
                },
                plot_bgcolor: 'rgba(26,26,26,0.5)',
                paper_bgcolor: 'rgba(26,26,26,0.5)',
                font: { color: '#f4e8d0' },
                legend: { bgcolor: 'rgba(26,26,26,0.8)' }
            };
            
            Plotly.newPlot('forecast-chart', traces, layout, {responsive: true});
            </script>
        </body>
        </html>
        """
        
        return render_template_string(template, forecast_data=forecast_data, styles=SHARED_STYLES)
        
    except Exception as e:
        import traceback
        return f"Forecast error: {str(e)}<br><pre>{traceback.format_exc()}</pre>", 500

@app.route('/export/pdf/analytics-report')
def export_pdf_report():
    """Generate comprehensive PDF analytics report"""
    try:
        from weasyprint import HTML
        import io
        from flask import send_file, request
        from datetime import datetime
        
        # Gather all analytics data
        import sys
        sys.path.insert(0, '/home/rod/home_ai_stack')
        from jvi_ml import get_ml_enhanced_rankings, load_models
        
        load_models()
        rankings = get_ml_enhanced_rankings(limit=50, sort_by='balanced')
        
        # Create HTML report
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Casino Analytics Report</title>
            <style>
                @page {{ size: A4; margin: 1cm; }}
                body {{ font-family: Arial, sans-serif; color: #333; }}
                h1 {{ color: #d4af37; border-bottom: 3px solid #d4af37; padding-bottom: 10px; }}
                h2 {{ color: #cd7f32; margin-top: 30px; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th {{ background: #d4af37; color: white; padding: 10px; text-align: left; }}
                td {{ padding: 8px; border-bottom: 1px solid #ddd; }}
                tr:nth-child(even) {{ background: #f9f9f9; }}
                .cluster-badge {{ padding: 3px 8px; border-radius: 3px; font-size: 0.85em; font-weight: bold; }}
                .cluster-big {{ background: #ff6b6b; color: white; }}
                .cluster-fast {{ background: #4dabf7; color: white; }}
                .cluster-high {{ background: #20c997; color: white; }}
                .cluster-balanced {{ background: #ffd43b; color: #333; }}
            </style>
        </head>
        <body>
            <h1>🎰 Casino Analytics Report</h1>
            <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>Total Machines Analyzed:</strong> {len(rankings)}</p>
            
            <h2>Top 20 JVI Rankings (ML-Enhanced)</h2>
            <table>
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Machine</th>
                        <th>Cluster</th>
                        <th>JVI</th>
                        <th>Predicted</th>
                        <th>Growth</th>
                        <th>Hits</th>
                        <th>Avg Payout</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for i, m in enumerate(rankings[:20], 1):
            cluster_class = m.get('ml_cluster', 'Balanced').lower().replace(' ', '-').split()[0]
            html_content += f"""
                    <tr>
                        <td>{i}</td>
                        <td>{m['machine_name'][:40]}</td>
                        <td><span class="cluster-badge cluster-{cluster_class}">{m.get('ml_cluster', 'N/A')}</span></td>
                        <td>{m.get('jvi_balanced', 0):.0f}</td>
                        <td>{m.get('predicted_jvi', 0):.0f}</td>
                        <td>{m.get('jvi_growth', 0):+.0f}</td>
                        <td>{m.get('hits', 0)}</td>
                        <td>${m.get('avg_jackpot', 0):,.0f}</td>
                    </tr>
            """
        
        html_content += """
                </tbody>
            </table>
            
            <h2>Cluster Distribution</h2>
            <p>Machines are automatically clustered using KMeans ML algorithm based on behavioral patterns.</p>
        </body>
        </html>
        """
        
        # Generate PDF
        pdf = HTML(string=html_content, base_url=request.url_root).write_pdf()
        
        # Send as download
        pdf_buffer = io.BytesIO(pdf)
        pdf_buffer.seek(0)
        
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'casino_analytics_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        )
        
    except Exception as e:
        import traceback
        return f"PDF generation error: {str(e)}<br><pre>{traceback.format_exc()}</pre>", 500

@app.route('/export/csv/jvi-rankings')
def export_jvi_csv():
    """Export JVI rankings as CSV - ALL machines"""
    try:
        import sys
        import io
        from flask import send_file
        from datetime import datetime
        sys.path.insert(0, '/home/rod/home_ai_stack')
        from jvi_ml import get_ml_enhanced_rankings, load_models
        
        # Load models and get ALL rankings (no limit)
        load_models()
        rankings = get_ml_enhanced_rankings(limit=1000, sort_by='balanced')  # Get all machines
        
        # Convert to DataFrame
        df = pd.DataFrame(rankings)
        
        # Select relevant columns
        columns = ['machine_name', 'denomination', 'bank', 'hits', 'total_payout', 
                  'avg_jackpot', 'max_jackpot', 'jvi_balanced', 'predicted_jvi', 
                  'pred_low', 'pred_high', 'jvi_growth', 'ml_cluster']
        
        # Filter to existing columns
        export_cols = [c for c in columns if c in df.columns]
        df_export = df[export_cols]
        
        # Create CSV in memory
        csv_buffer = io.StringIO()
        df_export.to_csv(csv_buffer, index=False)
        csv_data = csv_buffer.getvalue()
        
        # Convert to bytes
        bytes_buffer = io.BytesIO(csv_data.encode('utf-8'))
        bytes_buffer.seek(0)
        
        return send_file(
            bytes_buffer,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'jvi_rankings_all_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )
        
    except Exception as e:
        import traceback
        return f"Export error: {str(e)}<br><pre>{traceback.format_exc()}</pre>", 500

@app.route('/import-data', methods=['GET'])
def import_data():
    """Import legacy CSV data"""
    conn = get_db_connection()
    if not conn:
        return "DB error", 500
    cur = conn.cursor()

    try:
        # Load CSV (expected in app root)
        import os
        if not os.path.exists('jackpot_raw_clean.csv'):
            return "Error: jackpot_raw_clean.csv not found in server directory.", 404

        df = pd.read_csv('jackpot_raw_clean.csv')
        # Ensure regex formatting or specific date parsing if needed
        df['hit_timestamp'] = pd.to_datetime(df['datetime'], format='%m/%d/%Y %H:%M:%S', errors='coerce')
        df['location_id'] = df['bank'] 
        
        inserted = 0
        for _, row in df.iterrows():
            if pd.isnull(row['hit_timestamp']):
                continue
                
            try:
                machine = row.get('machine_name', 'Unknown')
                denom = row.get('denomination', 'Unknown')
                amount = row.get('amount', 0)
                
                # Clean amount
                if isinstance(amount, str):
                    amount = float(amount.replace('$', '').replace(',', ''))
                
                cur.execute("""
                    INSERT INTO jackpots (location_id, machine_name, denomination, amount, hit_timestamp, scraped_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (row['bank'], machine, denom, amount, row['hit_timestamp'], datetime.now()))
                inserted += cur.rowcount
            except Exception:
                pass

        conn.commit()
        cur.close()
        conn.close()
        return f"✅ Imported {inserted} new jackpots!"
        
    except Exception as e:
        return f"Import failed: {str(e)}", 500

if __name__ == '__main__':
    print("🧙 INITIALIZING THE ONE DASHBOARD...")
    print("⛏️ Mithril: Bitcoin & Crypto (TradingView)")
    print("💰 Treasures: Fed Treasury (Bills, Bonds, Notes)")
    print("🏛️ Markets: NASDAQ & Economic Indicators")
    print("🎰 Treasure Hunter: Casino Jackpots")
    print("📊 Access at: http://192.168.1.211:8004")
    
    # Data ingestion now handled by systemd services:
    # - coushatta-scraper.timer (every 5 minutes)
    # - multi-casino-scraper.timer (every 15 minutes)
    init_jackpot_table()
    cleanup_jackpot_data()
    
    # Multi-casino jackpots route
    @app.route('/multi-casino')
    def multi_casino():
        """Display jackpots from multiple casinos"""
        conn = get_db_connection()
        if not conn:
            return "Database error", 500
        
        try:
            from psycopg2.extras import RealDictCursor
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("""
                SELECT casino, machine_name, amount, date_text, source_url, scraped_at
                FROM multi_casino_jackpots
                ORDER BY scraped_at DESC
                LIMIT 100
            """)
            jackpots = cur.fetchall()
            cur.close()
            conn.close()
            
            template = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Multi-Casino Jackpots</title>
                {{ styles|safe }}
            </head>
            <body>
                <div class="container">
                    <a href="/" style="font-size: 1.1em; margin-bottom: 20px; display: inline-block;">← Back to Dashboard</a>
                    
                    <h1 class="text-center mb-4">🎰 Multi-Casino Jackpots 🎰</h1>
                    <p class="text-center" style="color: #888; margin-bottom: 30px;">Latest jackpots from 7 casino properties</p>
                    
                    <div class="card p-4">
                        <div class="table-responsive">
                            <table class="table table-dark table-hover">
                                <thead>
                                    <tr style="color: var(--text-gold); border-bottom: 2px solid #555;">
                                        <th>Casino</th>
                                        <th>Machine/Game</th>
                                        <th>Amount</th>
                                        <th>Date</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {% for jp in jackpots %}
                                    <tr>
                                        <td><strong>{{ jp.casino }}</strong></td>
                                        <td>{{ jp.machine_name }}</td>
                                        <td style="color: var(--accent);">${{ "{:,.2f}".format(jp.amount) if jp.amount else "N/A" }}</td>
                                        <td>{{ jp.scraped_at.strftime('%m/%d %I:%M %p') if jp.scraped_at else jp.date_text or 'N/A' }}</td>
                                    </tr>
                                    {% endfor %}
                                </tbody>
                            </table>
                        </div>
                    </div>
                    
                    <p class="text-center mt-4" style="color: #666; font-size: 0.9em;">
                        Live Data Feed (Updates 5-15 mins) • Total: {{ jackpots|length }} jackpots
                    </p>
                </div>
            </body>
            </html>
            """
            
            return render_template_string(template, jackpots=jackpots, styles=SHARED_STYLES)
            
        except Exception as e:
            return f"Error: {e}", 500
    
    app.run(host='0.0.0.0', port=8004, debug=True)