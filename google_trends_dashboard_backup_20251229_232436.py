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

app = Flask(__name__)

# PostgreSQL connection for casino jackpots (Unix socket)
DB_CONFIG = {'database': 'postgres', 'user': 'rod'}

# Global cache for jackpots
jackpot_cache = []
jackpot_cache_time = None
initial_scrape_done = False

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

def scrape_jackpot_page(page_num):
    try:
        url = f"https://www.coushattacasinoresort.com/gaming/slot-jackpot-updates/page/{page_num}"
        response = requests.get(url, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')
        jackpots = []
        
        # Find all data rows
        for row in soup.find_all('tr', class_='dataRow'):
            try:
                # Extract from caption
                caption = row.find('span', class_='caption')
                if not caption:
                    continue
                
                caption_text = caption.get_text()
                
                # Extract machine name
                if 'Title:' in caption_text:
                    machine_name = caption_text.split('Title:')[1].split('Amount:')[0].strip()
                else:
                    machine_name = 'Unknown'
                
                # Extract amount
                amount = None
                if 'Amount:' in caption_text:
                    amount_str = caption_text.split('Amount:')[1].split('Denomination:')[0].strip()
                    amount_str = amount_str.replace('$', '').replace(',', '')
                    try:
                        amount = float(amount_str)
                    except:
                        amount = None
                
                # Extract denomination
                if 'Denomination:' in caption_text:
                    denomination = caption_text.split('Denomination:')[1].split('Game ID:')[0].strip()
                else:
                    denomination = 'Unknown'
                
                # Extract game ID
                game_id = None
                if 'Game ID:' in caption_text:
                    game_id = caption_text.split('Game ID:')[1].split('Location:')[0].strip()
                
                # Extract location
                if 'Location:' in caption_text:
                    location_id = caption_text.split('Location:')[1].strip()
                else:
                    location_id = 'Unknown'
                
                # Extract timestamp from the span after caption
                hit_timestamp = None
                timestamp_span = row.find('span', class_='slotTitle')
                if timestamp_span:
                    timestamp_text = timestamp_span.get_text()
                    # Extract date/time (format: 12/29/2025 16:57:12)
                    import re
                    match = re.search(r'(\d{1,2}/\d{1,2}/\d{4} \d{1,2}:\d{2}:\d{2})', timestamp_text)
                    if match:
                        try:
                            hit_timestamp = datetime.strptime(match.group(1), '%m/%d/%Y %H:%M:%S')
                        except:
                            pass
                
                jackpots.append({
                    'location_id': location_id,
                    'machine_name': machine_name,
                    'denomination': denomination,
                    'amount': amount,
                    'game_id': game_id,
                    'hit_timestamp': hit_timestamp,
                    'page_num': page_num
                })
            except Exception as e:
                continue
        
        return jackpots
    except Exception as e:
        print(f"Error scraping page {page_num}: {e}")
        return []

def scrape_all_pages_initial():
    global initial_scrape_done
    print("🎰 Starting initial scrape of all 62 pages...")
    conn = get_db_connection()
    if not conn:
        print("❌ No DB connection, skipping initial scrape")
        return
    cur = conn.cursor()
    total_jackpots = 0
    for page in range(1, 63):
        jackpots = scrape_jackpot_page(page)
        for jp in jackpots:
            try:
                cur.execute("""
                    INSERT INTO jackpots (location_id, machine_name, denomination, amount, game_id, hit_timestamp, page_num)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (location_id, machine_name, hit_timestamp, amount) DO NOTHING
                """, (jp['location_id'], jp['machine_name'], jp['denomination'], jp.get('amount'), 
                      jp.get('game_id'), jp.get('hit_timestamp'), jp['page_num']))
                if cur.rowcount > 0:
                    total_jackpots += 1
            except:
                pass
        if page % 10 == 0:
            print(f"  Scraped {page}/62 pages...")
            conn.commit()
        time.sleep(0.5)
    conn.commit()
    cur.close()
    conn.close()
    initial_scrape_done = True
    print(f"✅ Initial scrape complete! Loaded {total_jackpots} jackpots")

def get_jackpots():
    global jackpot_cache, jackpot_cache_time
    if jackpot_cache and jackpot_cache_time:
        if (datetime.now() - jackpot_cache_time).seconds < 300:
            return jackpot_cache
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("SELECT location_id, machine_name, denomination, scraped_at, amount, hit_timestamp FROM jackpots ORDER BY hit_timestamp DESC NULLS LAST, scraped_at DESC LIMIT 50")
            jackpots = cur.fetchall()
            cur.close()
            conn.close()
            jackpot_cache = [dict(jp) for jp in jackpots]
            jackpot_cache_time = datetime.now()
            if jackpots and initial_scrape_done:
                threading.Thread(target=refresh_page_one, daemon=True).start()
            return jackpot_cache
        except Exception as e:
            print(f"Error fetching jackpots: {e}")
    return [{'location_id': 'HD0104', 'machine_name': 'IGT MULTI-GAME', 'denomination': '$1.00', 'scraped_at': datetime.now()}]

def get_jackpot_stats():
    """Get comprehensive casino jackpot statistics"""
    conn = get_db_connection()
    if not conn:
        return {
            'hot_areas': [], 'top_machines': [], 'top_denoms': [], 
            'total_jackpots': 0, 'recent_count': 0, 'best_machines': [],
            'avg_jackpot': 0, 'median_jackpot': 0, 'max_jackpot': 0,
            'high_limit': {'count': 0, 'avg': 0, 'max': 0, 'best_machines': [], 'recommended': []}
        }
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Overall statistics
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                ROUND(AVG(amount), 2) as avg_amount,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY amount) as median_amount,
                MIN(amount) as min_amount,
                MAX(amount) as max_amount
            FROM jackpots
            WHERE amount IS NOT NULL
        """)
        overall = dict(cur.fetchone() or {})
        
        # High Limit Room Statistics (jackpots >= $10,000)
        cur.execute("""
            SELECT 
                COUNT(*) as count,
                ROUND(AVG(amount), 2) as avg_amount,
                MAX(amount) as max_amount,
                MIN(amount) as min_amount
            FROM jackpots
            WHERE amount >= 10000
        """)
        high_limit_overall = dict(cur.fetchone() or {})
        
        # Best high-limit machines
        cur.execute("""
            SELECT 
                machine_name,
                COUNT(*) as hit_count,
                ROUND(AVG(amount), 2) as avg_payout,
                MAX(amount) as max_payout,
                denomination
            FROM jackpots
            WHERE amount >= 10000
            GROUP BY machine_name, denomination
            HAVING COUNT(*) >= 2
            ORDER BY avg_payout DESC
            LIMIT 10
        """)
        high_limit_best = [dict(row) for row in cur.fetchall()]
        
        # Recommended high-limit machines
        cur.execute("""
            SELECT 
                machine_name,
                denomination,
                COUNT(*) as hit_count,
                ROUND(AVG(amount), 2) as avg_payout,
                MAX(amount) as max_payout,
                ROUND(COUNT(*) * AVG(amount) / 10000, 2) as score
            FROM jackpots
            WHERE amount >= 10000
            GROUP BY machine_name, denomination
            HAVING COUNT(*) >= 3
            ORDER BY score DESC
            LIMIT 5
        """)
        high_limit_recommended = [dict(row) for row in cur.fetchall()]
        
        # Hot areas (locations with most jackpots)
        cur.execute("""
            SELECT location_id, COUNT(*) as jackpot_count, ROUND(AVG(amount), 2) as avg_amount
            FROM jackpots
            WHERE amount IS NOT NULL
            GROUP BY location_id
            ORDER BY jackpot_count DESC
            LIMIT 10
        """)
        hot_areas = [dict(row) for row in cur.fetchall()]
        
        # Best machines by average payout (min 3 hits for statistical significance)
        cur.execute("""
            SELECT 
                machine_name,
                COUNT(*) as hit_count,
                ROUND(AVG(amount), 2) as avg_payout,
                MIN(amount) as min_payout,
                MAX(amount) as max_payout,
                denomination
            FROM jackpots
            WHERE amount IS NOT NULL
            GROUP BY machine_name, denomination
            HAVING COUNT(*) >= 3
            ORDER BY avg_payout DESC
            LIMIT 15
        """)
        best_machines = [dict(row) for row in cur.fetchall()]
        
        # Most frequent hitters (machines that pay out most often)
        cur.execute("""
            SELECT 
                machine_name,
                COUNT(*) as hit_count,
                ROUND(AVG(amount), 2) as avg_payout,
                denomination
            FROM jackpots
            WHERE amount IS NOT NULL
            GROUP BY machine_name, denomination
            ORDER BY hit_count DESC
            LIMIT 10
        """)
        top_machines = [dict(row) for row in cur.fetchall()]
        
        # Best ROI by denomination (avg payout / denomination)
        cur.execute("""
            SELECT 
                denomination,
                COUNT(*) as count,
                ROUND(AVG(amount), 2) as avg_payout,
                ROUND(MAX(amount), 2) as max_payout
            FROM jackpots
            WHERE amount IS NOT NULL AND denomination != 'Unknown'
            GROUP BY denomination
            ORDER BY avg_payout DESC
            LIMIT 10
        """)
        top_denoms = [dict(row) for row in cur.fetchall()]
        
        # Recent activity (last hour)
        cur.execute("""
            SELECT COUNT(*) as recent
            FROM jackpots
            WHERE scraped_at > NOW() - INTERVAL '1 hour'
        """)
        recent_count = cur.fetchone()['recent']
        
        # Activity by 15-minute increments (last 2 hours)
        cur.execute("""
            SELECT 
                EXTRACT(EPOCH FROM (NOW() - scraped_at)) / 900 as interval_num,
                COUNT(*) as hit_count
            FROM jackpots
            WHERE scraped_at > NOW() - INTERVAL '2 hours'
            GROUP BY interval_num
            ORDER BY interval_num
        """)
        activity_data = cur.fetchall()
        
        # Convert to time-based format
        activity_by_time = []
        for i in range(8):  # 8 intervals = 2 hours
            minutes_ago = (7 - i) * 15
            count = 0
            for row in activity_data:
                if int(row['interval_num']) == i:
                    count = row['hit_count']
                    break
            if minutes_ago == 0:
                label = 'Now'
            elif minutes_ago < 60:
                label = f'{minutes_ago}m ago'
            else:
                hours = minutes_ago // 60
                mins = minutes_ago % 60
                label = f'{hours}h{mins}m ago' if mins > 0 else f'{hours}h ago'
            activity_by_time.append({'label': label, 'count': count})
        
        # Best time to play (jackpots by hour of day)
        cur.execute("""
            SELECT 
                EXTRACT(HOUR FROM hit_timestamp) as hour,
                COUNT(*) as hit_count,
                ROUND(AVG(amount), 2) as avg_payout
            FROM jackpots
            WHERE hit_timestamp IS NOT NULL
            GROUP BY hour
            ORDER BY hit_count DESC
            LIMIT 24
        """)
        best_hours_data = cur.fetchall()
        
        # Format best hours
        best_hours = []
        for row in best_hours_data[:5]:  # Top 5 hours
            hour = int(row['hour'])
            if hour == 0:
                time_str = '12 AM'
            elif hour < 12:
                time_str = f'{hour} AM'
            elif hour == 12:
                time_str = '12 PM'
            else:
                time_str = f'{hour-12} PM'
            best_hours.append({
                'time': time_str,
                'hits': row['hit_count'],
                'avg_payout': float(row['avg_payout'] or 0)
            })
        
        # Zone Performance (by location prefix)
        cur.execute("""
            SELECT 
                LEFT(location_id, 2) as zone, 
                COUNT(*) as hits, 
                ROUND(AVG(amount), 2) as avg_payout,
                MAX(amount) as max_payout
            FROM jackpots 
            WHERE location_id IS NOT NULL 
            GROUP BY zone 
            ORDER BY hits DESC 
            LIMIT 6
        """)
        zones = [dict(row) for row in cur.fetchall()]
        
        # Game Families (Group by first word)
        cur.execute("""
            SELECT 
                split_part(machine_name, ' ', 1) as family, 
                COUNT(*) as hits, 
                ROUND(AVG(amount), 2) as avg_payout
            FROM jackpots 
            WHERE amount IS NOT NULL 
            GROUP BY family 
            ORDER BY hits DESC 
            LIMIT 5
        """)
        game_families = [dict(row) for row in cur.fetchall()]
        
        # Cold Machines (Sleeping Giants - popular machines with no recent hits)
        cur.execute("""
            SELECT 
                machine_name, 
                MAX(hit_timestamp) as last_hit, 
                COUNT(*) as historic_hits,
                EXTRACT(EPOCH FROM (NOW() - MAX(hit_timestamp))) / 3600 as hours_since_hit
            FROM jackpots 
            GROUP BY machine_name 
            HAVING COUNT(*) > 10 
            AND MAX(hit_timestamp) < NOW() - INTERVAL '24 hours' 
            ORDER BY historic_hits DESC 
            LIMIT 5
        """)
        cold_machines = []
        for row in cur.fetchall():
            hours = int(row['hours_since_hit'] or 0)
            days = hours // 24
            time_str = f"{days}d {hours%24}h" if days > 0 else f"{hours}h"
            cold_machines.append({
                'machine_name': row['machine_name'],
                'last_hit': row['last_hit'],
                'historic_hits': row['historic_hits'],
                'time_since': time_str
            })
            
        # Recommended machines (best combination of frequency + payout)
        cur.execute("""
            SELECT 
                machine_name,
                denomination,
                COUNT(*) as hit_count,
                ROUND(AVG(amount), 2) as avg_payout,
                ROUND(MAX(amount), 2) as max_payout,
                ROUND(COUNT(*) * AVG(amount) / 1000, 2) as score
            FROM jackpots
            WHERE amount IS NOT NULL
            GROUP BY machine_name, denomination
            HAVING COUNT(*) >= 5
            ORDER BY score DESC
            LIMIT 5
        """)
        recommended = [dict(row) for row in cur.fetchall()]
        
        cur.close()
        conn.close()
        
        return {
            'hot_areas': hot_areas,
            'top_machines': top_machines,
            'best_machines': best_machines,
            'top_denoms': top_denoms,
            'recommended': recommended,
            'total_jackpots': overall.get('total', 0),
            'recent_count': recent_count,
            'activity_by_time': activity_by_time,
            'best_hours': best_hours,
            'zones': zones,
            'game_families': game_families,
            'cold_machines': cold_machines,
            'avg_jackpot': float(overall.get('avg_amount', 0) or 0),
            'median_jackpot': float(overall.get('median_amount', 0) or 0),
            'min_jackpot': float(overall.get('min_amount', 0) or 0),
            'max_jackpot': float(overall.get('max_amount', 0) or 0),
            'high_limit': {
                'count': high_limit_overall.get('count', 0),
                'avg': float(high_limit_overall.get('avg_amount', 0) or 0),
                'max': float(high_limit_overall.get('max_amount', 0) or 0),
                'min': float(high_limit_overall.get('min_amount', 0) or 0),
                'best_machines': high_limit_best,
                'recommended': high_limit_recommended
            }
        }
    except Exception as e:
        print(f"Error getting stats: {e}")
        return {
            'hot_areas': [], 'top_machines': [], 'top_denoms': [], 'best_machines': [],
            'total_jackpots': 0, 'recent_count': 0, 'recommended': [], 'activity_by_time': [], 'best_hours': [],
            'zones': [], 'game_families': [], 'cold_machines': [],
            'avg_jackpot': 0, 'median_jackpot': 0, 'max_jackpot': 0,
            'high_limit': {'count': 0, 'avg': 0, 'max': 0, 'best_machines': [], 'recommended': []}
        }



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


def get_all_machine_stats():
    """Get stats for all machines for rankings"""
    conn = get_db_connection()
    if not conn:
        return []
        
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT 
                machine_name,
                location_id,
                COUNT(*) as hits,
                ROUND(AVG(amount), 2) as avg_payout,
                MAX(amount) as max_payout,
                SUM(amount) as total_payout,
                MAX(hit_timestamp) as last_hit
            FROM jackpots
            WHERE amount IS NOT NULL
            GROUP BY machine_name, location_id
            HAVING COUNT(*) > 1
            ORDER BY avg_payout DESC
            LIMIT 100
        """)
        return [dict(row) for row in cur.fetchall()]
    except Exception as e:
        print(f"Error getting ranking stats: {e}")
        return []
    finally:
        cur.close()
        conn.close()

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
            'volatility': float(df['amount'].std() if len(df) > 1 else 0),
            'denomination': df['denomination'].iloc[0],
            'location_id': df['location_id'].iloc[0]
        }
        
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
        labels = ['Small (<$2k)', 'Medium ($2k-$5k)', 'Big ($5k-$10k)', 'Jackpot ($10k+)']
        df['win_bucket'] = pd.cut(df['amount'], bins=bins, labels=labels)
        dist = [{'label': k, 'count': v} for k,v in df['win_bucket'].value_counts().items() if v > 0]
        
        # Best Times
        df['hour'] = df['hit_timestamp'].dt.hour
        hourly = df.groupby('hour')['amount'].agg(['count', 'mean'])
        best_hours = []
        for h, row in hourly.nlargest(5, 'count').iterrows():
            time_str = f"{h-12} PM" if h > 12 else (f"{h} AM" if h > 0 else "12 AM")
            if h == 12: time_str = "12 PM"
            best_hours.append({'time': time_str, 'hits': int(row['count']), 'avg': float(row['mean'])})
            
        cv = summary['volatility'] / summary['avg_payout'] if summary['avg_payout'] > 0 else 0
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
        print(f"Error getting details: {e}")
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
            cur.execute("""
                INSERT INTO jackpots (location_id, machine_name, denomination, amount, game_id, hit_timestamp, page_num)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (jp['location_id'], jp['machine_name'], jp['denomination'], jp.get('amount'),
                  jp.get('game_id'), jp.get('hit_timestamp'), jp['page_num']))
        except:
            pass
    conn.commit()
    cur.close()
    conn.close()
    print("🔄 Refreshed page 1 jackpots")

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
    demo_data = [{'title': 'AI Breakthroughs 2025', 'traffic': 'HOT'}, {'title': 'Quantum Computing', 'traffic': 'HOT'}, {'title': 'Space Exploration', 'traffic': 'HOT'}, {'title': 'Climate Tech', 'traffic': 'HOT'}, {'title': 'Neural Interfaces', 'traffic': 'HOT'}]
    try:
        pytrends = TrendReq(hl='en-US', tz=360, timeout=(10, 25), retries=2)
        trending = pytrends.trending_searches(pn=geo)
        result = [{'title': item, 'traffic': 'HOT'} for item in trending[0].head(5).tolist()]
        return result if result else demo_data
    except Exception as e:
        print(f"Using demo data for {geo}: {e}")
        return demo_data

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
            <li class="nav-item"><button class="nav-link active" data-bs-toggle="tab" data-bs-target="#trends">📜 Chronicles</button></li>
            <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#crypto">⛏️ Mithril</button></li>
            <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#treasury">💰 Treasures</button></li>
            <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#markets">🏛️ Markets</button></li>
            <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#news">📰 Tidings</button></li>
            <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#links">🗺️ Paths</button></li>
            <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#jackpots">🎰 Treasure Hunter</button></li>
        </ul>
        
        <div class="tab-content">
            <!-- Chronicles Tab (Google Trends) -->
            <div class="tab-pane fade show active" id="trends">
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
            <div class="tab-pane fade" id="jackpots">
                <div class="row">
                    <!-- Statistics Column -->
                    <div class="col-md-5">
                        <div class="scroll-card">
                            <h2 class="card-title">📊 Casino Analytics</h2>
                            
                            <!-- Overall Stats -->
                            <div style="background: linear-gradient(135deg, rgba(212, 175, 55, 0.15), rgba(205, 127, 50, 0.1)); padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; text-align: center;">
                                    <div>
                                        <div style="font-size: 1.8em; color: var(--gold); font-family: 'Cinzel', serif;">${{ "%.2f"|format(stats.avg_jackpot) }}</div>
                                        <div style="font-size: 0.8em; color: rgba(244, 232, 208, 0.7);">Avg Jackpot</div>
                                    </div>
                                    <div>
                                        <div style="font-size: 1.8em; color: var(--bronze); font-family: 'Cinzel', serif;">${{ "%.2f"|format(stats.median_jackpot) }}</div>
                                        <div style="font-size: 0.8em; color: rgba(244, 232, 208, 0.7);">Median</div>
                                    </div>
                                    <div>
                                        <div style="font-size: 1.3em; color: #00ff9f; font-family: 'Cinzel', serif;">${{ "%.2f"|format(stats.max_jackpot) }}</div>
                                        <div style="font-size: 0.75em; color: rgba(244, 232, 208, 0.7);">Max Payout</div>
                                    </div>
                                    <div>
                                        <div style="font-size: 1.3em; color: var(--parchment); font-family: 'Cinzel', serif;">{{ stats.total_jackpots }}</div>
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
                            {% for rec in stats.recommended[:3] %}
                            <div style="padding: 10px; margin: 8px 0; background: linear-gradient(90deg, rgba(0, 255, 159, 0.15), rgba(0, 255, 159, 0.05)); border-left: 4px solid #00ff9f; border-radius: 4px;">
                                <div style="margin-bottom: 5px;">
                                    <a href="/machine/{{ rec.machine_name }}" style="color: #00ff9f; font-weight: 700; font-size: 0.95em; text-decoration: none; border-bottom: 1px dotted #00ff9f;">{{ rec.machine_name[:35] }}</a>
                                </div>
                                <div style="display: flex; justify-content: space-between; font-size: 0.85em;">
                                    <span style="color: rgba(244, 232, 208, 0.9);">{{ rec.denomination }}</span>
                                    <span style="color: var(--gold); font-weight: 700;">Avg: ${{ "%.2f"|format(rec.avg_payout) }}</span>
                                </div>
                                <div style="font-size: 0.75em; color: rgba(244, 232, 208, 0.7); margin-top: 3px;">{{ rec.hit_count }} hits • Max: ${{ "%.2f"|format(rec.max_payout) }}</div>
                            </div>
                            {% endfor %}
                            
                            <!-- High Limit Room -->
                            <div style="background: linear-gradient(135deg, rgba(255, 215, 0, 0.2), rgba(255, 215, 0, 0.05)); padding: 15px; border-radius: 8px; margin-top: 25px; border: 2px solid gold;">
                                <h3 style="font-family: 'Cinzel', serif; font-size: 1.2em; color: gold; margin-bottom: 15px; text-align: center; text-shadow: 0 0 10px rgba(255, 215, 0, 0.5);">👑 HIGH LIMIT ROOM 👑</h3>
                                <p style="font-size: 0.75em; color: rgba(244, 232, 208, 0.8); text-align: center; margin-bottom: 15px;">Jackpots $10,000+</p>
                                
                                <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; text-align: center; margin-bottom: 15px;">
                                    <div>
                                        <div style="font-size: 1.3em; color: gold; font-family: 'Cinzel', serif;">{{ stats.high_limit.count }}</div>
                                        <div style="font-size: 0.7em; color: rgba(244, 232, 208, 0.7);">Total Hits</div>
                                    </div>
                                    <div>
                                        <div style="font-size: 1.3em; color: gold; font-family: 'Cinzel', serif;">${{ "%.0f"|format(stats.high_limit.avg) }}</div>
                                        <div style="font-size: 0.7em; color: rgba(244, 232, 208, 0.7);">Avg Payout</div>
                                    </div>
                                    <div>
                                        <div style="font-size: 1.3em; color: #00ff9f; font-family: 'Cinzel', serif;">${{ "%.0f"|format(stats.high_limit.max) }}</div>
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
                                        <span style="color: #00ff9f; font-weight: 700;">${{ "%.0f"|format(hl.avg_payout) }}</span>
                                    </div>
                                    <div style="font-size: 0.7em; color: rgba(244, 232, 208, 0.6); margin-top: 2px;">{{ hl.hit_count }} hits • Max: ${{ "%.0f"|format(hl.max_payout) }}</div>
                                </div>
                                {% endfor %}
                                {% endif %}
                            </div>
                            
                            <!-- Best Time to Play -->
                            {% if stats.best_hours %}
                            <h3 style="font-family: 'Cinzel', serif; font-size: 1.1em; color: var(--gold); margin-top: 20px; margin-bottom: 10px; border-bottom: 1px solid var(--bronze); padding-bottom: 5px;">⏰ Best Time to Play</h3>
                            <p style="font-size: 0.75em; color: rgba(244, 232, 208, 0.6); margin-bottom: 10px;">Based on historical jackpot frequency</p>
                            {% for hour in stats.best_hours %}
                            <div style="padding: 8px; margin: 5px 0; background: linear-gradient(90deg, rgba(212, 175, 55, 0.1), rgba(205, 127, 50, 0.05)); border-left: 3px solid var(--gold); display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <div style="color: var(--gold); font-weight: 700; font-size: 0.9em;">{{ hour.time }}</div>
                                    <div style="color: rgba(244, 232, 208, 0.7); font-size: 0.75em;">{{ hour.hits }} jackpots</div>
                                </div>
                                <div style="color: var(--bronze); font-size: 0.85em;">${{ "%.0f"|format(hour.avg_payout) }}</div>
                            </div>
                            {% endfor %}
                            {% endif %}
                            
                            <!-- Strategic Warfare Section (MOVED TO RIGHT COLUMN) -->
                                <h4 style="font-size: 0.95em; color: var(--parchment); margin-bottom: 10px; border-left: 3px solid var(--bronze); padding-left: 8px;">📍 Zone Control</h4>
                                <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 20px;">
                                    {% for zone in stats.zones %}
                                    <div style="flex: 1; min-width: 45%; background: rgba(0, 0, 0, 0.3); padding: 8px; border-radius: 4px; border: 1px solid rgba(212, 175, 55, 0.2);">
                                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                                            <span style="color: var(--gold); font-weight: 700;">{{ zone.zone }} {% if zone.zone == 'HD' %}(Hi-Lim){% endif %}</span>
                                            <span style="font-size: 0.8em; color: rgba(244, 232, 208, 0.6);">{{ zone.hits }} hits</span>
                                        </div>
                                        <div style="font-size: 0.8em; color: var(--bronze);">Avg: ${{ "%.0f"|format(zone.avg_payout) }}</div>
                                    </div>
                                    {% endfor %}
                                </div>
                                
                                <!-- Brand Wars -->
                                <h4 style="font-size: 0.95em; color: var(--parchment); margin-bottom: 10px; border-left: 3px solid var(--bronze); padding-left: 8px;">🐂 Battle of Brands</h4>
                                {% for family in stats.game_families %}
                                <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 0; border-bottom: 1px solid rgba(212, 175, 55, 0.1);">
                                    <span style="color: rgba(244, 232, 208, 0.8); font-size: 0.9em;">{{ family.family }}</span>
                                    <div style="text-align: right;">
                                        <div style="color: var(--gold); font-size: 0.85em; font-weight: 700;">${{ "%.0f"|format(family.avg_payout) }}</div>
                                        <div style="color: rgba(244, 232, 208, 0.5); font-size: 0.75em;">{{ family.hits }} hits</div>
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
                            </div>
                            
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
                            <h3 style="font-family: 'Cinzel', serif; font-size: 1.1em; color: var(--gold); margin-top: 20px; margin-bottom: 10px; border-bottom: 1px solid var(--bronze); padding-bottom: 5px;">🔥 Hottest Machines</h3>
                            {% for machine in stats.top_machines[:5] %}
                            <div style="padding: 8px; margin: 5px 0; background: linear-gradient(90deg, rgba(212, 175, 55, 0.1), rgba(205, 127, 50, 0.05)); border-left: 3px solid var(--gold);">
                                <div style="color: var(--parchment); font-size: 0.85em; margin-bottom: 3px;">{{ machine.machine_name[:30] }}...</div>
                                <div style="display: flex; justify-content: space-between; font-size: 0.8em;">
                                    <span style="color: var(--bronze);">{{ machine.hit_count }} hits</span>
                                    <span style="color: var(--gold);">Avg: ${{ "%.2f"|format(machine.avg_payout) }}</span>
                                </div>
                            </div>
                            {% endfor %}
                            
                            <!-- Best Denominations -->
                            <h3 style="font-family: 'Cinzel', serif; font-size: 1.1em; color: var(--gold); margin-top: 20px; margin-bottom: 10px; border-bottom: 1px solid var(--bronze); padding-bottom: 5px;">💵 Best Bet Sizes</h3>
                            {% for denom in stats.top_denoms[:5] %}
                            <div style="padding: 8px; margin: 5px 0; background: linear-gradient(90deg, rgba(212, 175, 55, 0.1), rgba(205, 127, 50, 0.05)); border-left: 3px solid var(--gold); display: flex; justify-content: space-between;">
                                <span style="color: var(--parchment);">{{ denom.denomination }}</span>
                                <span style="color: var(--gold); font-weight: 700;">${{ "%.2f"|format(denom.avg_payout) }}</span>
                            </div>
                            {% endfor %}
                        </div>
                    </div>
                    
                    <!-- Real-time Feed Column -->
                    <div class="col-md-7">
                        <div class="scroll-card">
                            <h2 class="card-title">🎰 Real-Time Jackpot Feed</h2>
                            <p style="text-align: center; color: rgba(244, 232, 208, 0.7); margin-bottom: 20px;">
                                Recent Slot Jackpots Over $1200 • Coushatta Casino Resort
                            </p>
                            <div style="max-height: 500px; overflow-y: auto;">
                                {% for jp in jackpots_data %}
                                <div class="jackpot-item">
                                    <div class="jackpot-machine">
                                        <a href="/machine/{{ jp.machine_name }}" style="color: inherit; text-decoration: none;">🎰 {{ jp.machine_name }}</a>
                                    </div>
                                    <div class="jackpot-details">
                                        {% if jp.amount %}
                                        <span style="color: #00ff9f; font-weight: 700; width: 100%; display: block; margin-bottom: 2px;">💰 ${{ "%.2f"|format(jp.amount) }}</span>
                                        {% endif %}
                                        <span>📍 {{ jp.location_id }}</span>
                                        <span>💵 {{ jp.denomination }}</span>
                                        <span>⏰ {{ jp.time_ago }}</span>
                                    </div>
                                </div>
                                {% endfor %}
                            </div>
                            
                            <!-- MOVED WIDGETS START -->
                            
                            <!-- Strategic Warfare Section -->
                            <div style="margin-top: 25px; border-top: 2px solid var(--bronze); padding-top: 15px;">
                                <h3 style="font-family: 'Cinzel', serif; font-size: 1.2em; color: var(--gold); margin-bottom: 15px; text-align: center; text-transform: uppercase; letter-spacing: 1px;">⚔️ Strategic Warfare ⚔️</h3>
                                
                                <!-- Zone Analysis -->
                                <h4 style="font-size: 0.95em; color: var(--parchment); margin-bottom: 10px; border-left: 3px solid var(--bronze); padding-left: 8px;">📍 Zone Control</h4>
                                <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 20px;">
                                    {% for zone in stats.zones %}
                                    <div style="flex: 1; min-width: 45%; background: rgba(0, 0, 0, 0.3); padding: 8px; border-radius: 4px; border: 1px solid rgba(212, 175, 55, 0.2);">
                                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                                            <span style="color: var(--gold); font-weight: 700;">{{ zone.zone }} {% if zone.zone == 'HD' %}(Hi-Lim){% endif %}</span>
                                            <span style="font-size: 0.8em; color: rgba(244, 232, 208, 0.6);">{{ zone.hits }} hits</span>
                                        </div>
                                        <div style="font-size: 0.8em; color: var(--bronze);">Avg: ${{ "%.0f"|format(zone.avg_payout) }}</div>
                                    </div>
                                    {% endfor %}
                                </div>
                                
                                <!-- Brand Wars -->
                                <h4 style="font-size: 0.95em; color: var(--parchment); margin-bottom: 10px; border-left: 3px solid var(--bronze); padding-left: 8px;">🐂 Battle of Brands</h4>
                                {% for family in stats.game_families %}
                                <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 0; border-bottom: 1px solid rgba(212, 175, 55, 0.1);">
                                    <span style="color: rgba(244, 232, 208, 0.8); font-size: 0.9em;">{{ family.family }}</span>
                                    <div style="text-align: right;">
                                        <div style="color: var(--gold); font-size: 0.85em; font-weight: 700;">${{ "%.0f"|format(family.avg_payout) }}</div>
                                        <div style="color: rgba(244, 232, 208, 0.5); font-size: 0.75em;">{{ family.hits }} hits</div>
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
                            </div>
                            
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
                            <h3 style="font-family: 'Cinzel', serif; font-size: 1.1em; color: var(--gold); margin-top: 20px; margin-bottom: 10px; border-bottom: 1px solid var(--bronze); padding-bottom: 5px;">🔥 Hottest Machines</h3>
                            {% for machine in stats.top_machines[:5] %}
                            <div style="padding: 8px; margin: 5px 0; background: linear-gradient(90deg, rgba(212, 175, 55, 0.1), rgba(205, 127, 50, 0.05)); border-left: 3px solid var(--gold);">
                                <div style="color: var(--parchment); font-size: 0.85em; margin-bottom: 3px;">{{ machine.machine_name[:30] }}...</div>
                                <div style="display: flex; justify-content: space-between; font-size: 0.8em;">
                                    <span style="color: var(--bronze);">{{ machine.hit_count }} hits</span>
                                    <span style="color: var(--gold);">Avg: ${{ "%.2f"|format(machine.avg_payout) }}</span>
                                </div>
                            </div>
                            {% endfor %}
                            
                            <!-- Best Denominations -->
                            <h3 style="font-family: 'Cinzel', serif; font-size: 1.1em; color: var(--gold); margin-top: 20px; margin-bottom: 10px; border-bottom: 1px solid var(--bronze); padding-bottom: 5px;">💵 Best Bet Sizes</h3>
                            {% for denom in stats.top_denoms[:5] %}
                            <div style="padding: 8px; margin: 5px 0; background: linear-gradient(90deg, rgba(212, 175, 55, 0.1), rgba(205, 127, 50, 0.05)); border-left: 3px solid var(--gold); display: flex; justify-content: space-between;">
                                <span style="color: var(--parchment);">{{ denom.denomination }}</span>
                                <span style="color: var(--gold); font-weight: 700;">${{ "%.2f"|format(denom.avg_payout) }}</span>
                            </div>
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
        const chartConfig = { type: 'bar', options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, grid: { color: 'rgba(212, 175, 55, 0.1)' }, ticks: { color: '#d4af37' } }, x: { grid: { display: false }, ticks: { color: '#d4af37' } } } } };
        new Chart(document.getElementById('usChart'), { ...chartConfig, data: { labels: {{ us_labels | tojson }}, datasets: [{ data: {{ us_values | tojson }}, backgroundColor: 'rgba(212, 175, 55, 0.6)', borderColor: '#d4af37', borderWidth: 2 }] } });
        new Chart(document.getElementById('globalChart'), { ...chartConfig, data: { labels: {{ global_labels | tojson }}, datasets: [{ data: {{ global_values | tojson }}, backgroundColor: 'rgba(205, 127, 50, 0.6)', borderColor: '#cd7f32', borderWidth: 2 }] } });
        setTimeout(() => location.reload(), 300000);
        let timeLeft = 300;
        setInterval(() => { timeLeft--; if (timeLeft <= 0) timeLeft = 300; const m = Math.floor(timeLeft / 60), s = timeLeft % 60; document.title = `⚔ The One Dashboard (${m}:${s.toString().padStart(2, '0')})`; }, 1000);
    </script>
</body>
</html>
"""

@app.route('/')
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
    
    us_labels = [item['title'][:15] + '...' if len(item['title']) > 15 else item['title'] for item in trending_us]
    us_values = [random.randint(70, 100) for _ in trending_us]
    global_labels = [item['title'][:15] + '...' if len(item['title']) > 15 else item['title'] for item in trending_global]
    global_values = [random.randint(70, 100) for _ in trending_global]
    update_time = datetime.now().strftime('%H:%M:%S')
    
    return render_template_string(HTML_TEMPLATE, trending_us=trending_us, trending_global=trending_global,
                                 news_data=news_data, services=services, jackpots_data=jackpots_data,
                                 stats=stats, us_labels=us_labels, us_values=us_values, 
                                 global_labels=global_labels, global_values=global_values, 
                                 update_time=update_time)


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
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@400;700&family=Lato:wght@400;700&display=swap" rel="stylesheet">
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            :root {
                --bg-dark: #0a0a0a;
                --text-gold: #d4af37;
                --text-light: #f4e8d0;
                --accent: #20c997;
            }
            body {
                background-color: var(--bg-dark);
                color: var(--text-light);
                font-family: 'Lato', sans-serif;
                padding: 20px;
            }
            h1, h2, h3 { font-family: 'Cinzel', serif; color: var(--text-gold); }
            .card {
                background: rgba(20, 20, 20, 0.95);
                border: 1px solid #333;
                box-shadow: 0 4px 6px rgba(0,0,0,0.5);
            }
            .table-dark {
                --bs-table-bg: transparent;
                color: #ccc;
            }
            .back-btn {
                color: var(--text-gold);
                text-decoration: none;
                font-size: 1.1em;
                display: inline-block;
                margin-bottom: 20px;
            }
        </style>
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
                                        {{ row.hits }}
                                    </div>
                                </td>
                                <td style="color: var(--accent);">${{ "%.0f"|format(row.avg) }}</td>
                                <td>${{ "%.0f"|format(row.max) }}</td>
                                <td>${{ "%.0f"|format(row.total) }}</td>
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
    return render_template_string(template, data=hourly_data)


@app.route('/payouts')
def payouts_ranking():
    machines = get_all_machine_stats()
    stats = get_jackpot_stats() # reuse for global stats if needed
    
    template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Machine Rankings & Payouts</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@400;700&family=Lato:wght@400;700&display=swap" rel="stylesheet">
        <style>
            :root {
                --bg-dark: #0a0a0a;
                --text-gold: #d4af37;
                --text-light: #f4e8d0;
                --accent: #20c997;
            }
            body {
                background-color: var(--bg-dark);
                color: var(--text-light);
                font-family: 'Lato', sans-serif;
                padding: 20px;
            }
            h1, h2, h3 { font-family: 'Cinzel', serif; color: var(--text-gold); }
            a { color: var(--text-gold); text-decoration: none; }
            a:hover { text-decoration: underline; color: #fff; }
            .card {
                background: rgba(20, 20, 20, 0.95);
                border: 1px solid #333;
                box-shadow: 0 4px 6px rgba(0,0,0,0.5);
            }
            .table-dark {
                --bs-table-bg: transparent;
                color: #ccc;
            }
            .rank-badge {
                width: 30px;
                height: 30px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 50%;
                background: rgba(255,255,255,0.1);
                font-weight: bold;
                color: #fff;
            }
            .rank-1 { background: #d4af37; color: #000; box-shadow: 0 0 10px #d4af37; }
            .rank-2 { background: #C0C0C0; color: #000; }
            .rank-3 { background: #CD7F32; color: #000; }
        </style>
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
                                <td class="text-end" style="font-size: 1.1em; color: var(--accent); font-weight: bold;">${{ "%.0f"|format(m.avg_payout) }}</td>
                                <td class="text-end" style="color: #ccc;">${{ "%.0f"|format(m.max_payout) }}</td>
                                <td class="text-end">
                                    <span style="background: rgba(212, 175, 55, 0.2); color: var(--text-gold); padding: 2px 8px; border-radius: 10px; font-size: 0.9em;">{{ m.hits }}</span>
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
    return render_template_string(template, machines=machines, stats=stats)

@app.route('/machine/<path:machine_name>')
def machine_detail(machine_name):
    # Decode URL-encoded machine name if necessary, though Flask handles path variables well
    details = get_machine_details(machine_name)
    if not details:
        return "Machine not found", 404
        
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
                    <span>📍 Zone: <strong style="color: var(--accent);">{{ details.summary.location_id }}</strong></span>
                    <span>💵 Denom: <strong style="color: var(--accent);">{{ details.summary.denomination }}</strong></span>
                    <span>⚡ Volatility: <strong style="color: {% if 'High' in details.volatility_rating %}#ff6b6b{% else %}#00ff9f{% endif %};">{{ details.volatility_rating }}</strong></span>
                    <span>🔥 Heat: <strong style="color: {% if 'HOT' in details.heat_rating %}#ff6b6b{% elif 'COLD' in details.heat_rating %}#4dabf7{% else %}#ffd43b{% endif %};">{{ details.heat_rating }}</strong></span>
                </div>
            </div>

            <div class="row g-3 mb-4">
                <div class="col-6 col-md-3">
                    <div class="metric-card">
                        <div class="metric-value">${{ "%.0f"|format(details.summary.avg_payout) }}</div>
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
                        <div class="metric-value">{{ details.summary.total_hits }}</div>
                        <div class="metric-label">Total Hits</div>
                    </div>
                </div>
                <div class="col-6 col-md-3">
                    <div class="metric-card">
                        <div class="metric-value">${{ "%.0f"|format(details.summary.max_payout) }}</div>
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
                            <span><strong style="color: var(--gold);">{{ hour.hits }} hits</strong> <small>(${{ "%.0f"|format(hour.avg) }} avg)</small></span>
                        </div>
                        {% endfor %}
                    </div>
                    {% else %}
                    <p style="color: #666;">Not enough data yet.</p>
                    {% endif %}
                    
                    <h3 style="font-size: 1.2em; border-bottom: 1px solid var(--bronze); padding-bottom: 8px; margin: 25px 0 15px 0;">📊 Win Distribution</h3>
                    {% for dist in details.distribution %}
                    <div style="margin-bottom: 5px; font-size: 0.9em; display: flex; justify-content: space-between;">
                        <span style="color: rgba(255,255,255,0.7);">{{ dist.label }}</span>
                        <span style="color: var(--accent);">{{ dist.count }} hits</span>
                    </div>
                    <div style="background: rgba(255,255,255,0.1); height: 6px; border-radius: 3px; overflow: hidden; margin-bottom: 10px;">
                        <div style="background: var(--gold); width: {{ (dist.count / details.summary.total_hits * 100)|int }}%; height: 100%;"></div>
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
                                    <td style="text-align: right; color: var(--accent);">${{ "%.2f"|format(hit.amount) }}</td>
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
    return render_template_string(MACHINE_TEMPLATE, machine_name=machine_name, details=details)

@app.route('/api/jackpots')
def api_jackpots():
    return jsonify(get_jackpots())

if __name__ == '__main__':
    print("🧙 INITIALIZING THE ONE DASHBOARD...")
    print("⛏️ Mithril: Bitcoin & Crypto (TradingView)")
    print("💰 Treasures: Fed Treasury (Bills, Bonds, Notes)")
    print("🏛️ Markets: NASDAQ & Economic Indicators")
    print("🎰 Treasure Hunter: Casino Jackpots")
    print("📊 Access at: http://192.168.1.211:8004")
    
    init_jackpot_table()
    if not initial_scrape_done:
        threading.Thread(target=scrape_all_pages_initial, daemon=True).start()
    
    app.run(host='0.0.0.0', port=8004, debug=False)
