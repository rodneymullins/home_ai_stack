import datetime
from datetime import datetime
from psycopg2.extras import RealDictCursor
from utils.db_pool import get_db_connection

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
            # Add color for dashboard if not present
            m['color'] = '#ffffff'
            
            if m['first_hit']:
                days_active = (datetime.now() - m['first_hit']).days
                if days_active < 30: days_active = 30
                daily_avg = m['hits'] / days_active
                expected = daily_avg * 30
                ratio = m['hits_30d'] / expected if expected > 0 else 0
                
                if ratio > 1.2: m['color'] = '#ff6b6b' # Red (Heating Up)
                elif ratio < 0.6: m['color'] = '#4dabf7' # Blue (Slowing Down)
                
                # Days per hit (using full active duration)
                m['days_per_hit'] = days_active / m['hits'] if m['hits'] > 0 else 0
            else:
                 m['days_per_hit'] = 0
                
        return results
    except Exception as e:
        print(f"Error getting ranking stats: {e}")
        return []
    finally:
        if conn:
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
        base_where = "machine_name NOT ILIKE '%%Poker%%' AND machine_name NOT ILIKE '%%Keno%%'"
        
        full_where = f"{where_clause} AND {base_where}" if where_clause else base_where
        if not where_clause: # Should not happen based on logic but safe
             full_where = f"1=1 AND {base_where}"

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
            WHERE {full_where} AND amount IS NOT NULL
        """, params)
        stats = dict(cur.fetchone() or {})
        
        # Check if we have data
        if not stats.get('hits'):
            # If no data, return empty structure (or None to trigger 404?)
            # Legacy code typically returned whatever statistics it found (often None/0)
            pass

        # Top Machines in Group
        conn.commit() # Clear transaction state if any
        cur.execute(f"""
            SELECT 
                machine_name,
                location_id,
                denomination,
                COUNT(*) as hits,
                ROUND(AVG(amount), 2) as avg_payout,
                MAX(amount) as max_payout
            FROM jackpots
            WHERE {full_where} AND amount IS NOT NULL
            GROUP BY machine_name, location_id, denomination
            ORDER BY hits DESC
            LIMIT 50
        """, params)
        top_machines = [dict(row) for row in cur.fetchall()]
        
        # Recent Hits
        cur.execute(f"""
            SELECT 
                machine_name,
                amount,
                hit_timestamp,
                location_id
            FROM jackpots
            WHERE {full_where} AND amount IS NOT NULL
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
        print(f"Error in get_group_details: {e}")
        return None
    finally:
         if conn:
            cur.close()
            conn.close()
