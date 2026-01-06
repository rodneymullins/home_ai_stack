from utils.db_pool import get_db_connection
from psycopg2.extras import RealDictCursor
import pandas as pd
from datetime import datetime
from services.stats_service import classify_manufacturer

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
        
        cur.close()
        conn.close()
        
        return {
            'summary': summary,
            'machines': machines,
            'recent_hits': recent_hits
        }
    except Exception as e:
        print(f"Error in get_bank_details: {e}")
        return None

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

def get_jackpot_clusters():
    # Stub for future implementation or missing function
    # print("Warning: get_jackpot_clusters is not implemented yet")
    return []

def get_hot_banks():
    # Stub for future implementation or missing function
    # print("Warning: get_hot_banks is not implemented yet")
    return []

def get_weekend_stats():
    """Get aggregate hit stats for weekend vs weekend"""
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT 
                is_weekend,
                COUNT(*) as hits,
                ROUND(AVG(amount), 2) as avg_payout
            FROM jackpots
            WHERE is_weekend IS NOT NULL
            GROUP BY is_weekend
        """)
        return list(cur.fetchall())
    except Exception as e:
        print(f"Error fetching weekend stats: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_hourly_details():
    """Get detailed hourly stats for 24-hour cycle analysis"""
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get aggregate stats by hour (0-23)
        cur.execute("""
            SELECT 
                EXTRACT(HOUR FROM hit_timestamp) as hour,
                COUNT(*) as hit_count,
                AVG(amount) as avg_payout,
                MAX(amount) as max_payout,
                SUM(amount) as total_payout
            FROM jackpots
            WHERE amount IS NOT NULL
            GROUP BY EXTRACT(HOUR FROM hit_timestamp)
            ORDER BY hour
        """)
        
        results = cur.fetchall()
        hourly_data = {int(r['hour']): r for r in results}
        
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
        if conn:
            cur.close()
            conn.close()
