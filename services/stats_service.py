import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from utils.db_pool import get_db_connection

def classify_manufacturer(machine_name):
    """Classify machine into manufacturer based on known game titles"""
    if not machine_name:
        return 'Other'
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
            WHERE amount IS NOT NULL AND machine_name NOT ILIKE '%Poker%' AND machine_name NOT ILIKE '%Keno%'
        """)
        overall = dict(cur.fetchone() or {})
        
        # High Limit Room Statistics (by floor location: HD prefix)
        cur.execute("""
            SELECT 
                COUNT(*) as count,
                ROUND(AVG(amount), 2) as avg_amount,
                MAX(amount) as max_amount,
                MIN(amount) as min_amount
            FROM jackpots
            WHERE location_id LIKE 'HD%' AND machine_name NOT ILIKE '%Poker%' AND machine_name NOT ILIKE '%Keno%'
        """)
        high_limit_overall = dict(cur.fetchone() or {})
        
        # Best high-limit machines (by floor location)
        cur.execute("""
            SELECT 
                machine_name,
                COUNT(*) as hit_count,
                ROUND(AVG(amount), 2) as avg_payout,
                MAX(amount) as max_payout,
                denomination
            FROM jackpots
            WHERE location_id LIKE 'HD%' AND machine_name NOT ILIKE '%Poker%' AND machine_name NOT ILIKE '%Keno%'
            GROUP BY machine_name, denomination
            HAVING COUNT(*) >= 2
            ORDER BY avg_payout DESC
            LIMIT 10
        """)
        high_limit_best = [dict(row) for row in cur.fetchall()]
        
        # Recommended high-limit machines (using 7-day recency, by floor location)
        cur.execute("""
            SELECT 
                machine_name,
                denomination,
                COUNT(*) as hit_count,
                ROUND(AVG(amount), 2) as avg_payout,
                MAX(amount) as max_payout,
                MAX(hit_timestamp) as latest_hit,
                COUNT(*) FILTER (WHERE hit_timestamp > NOW() - INTERVAL '7 days') as hits_7d,
                ROUND(COUNT(*) FILTER (WHERE hit_timestamp > NOW() - INTERVAL '7 days') * AVG(amount) / 1000, 2) as score
            FROM jackpots
            WHERE location_id LIKE 'HD%' AND machine_name NOT ILIKE '%Poker%' AND machine_name NOT ILIKE '%Keno%'
            GROUP BY machine_name, denomination
            HAVING COUNT(*) >= 2 AND COUNT(*) FILTER (WHERE hit_timestamp > NOW() - INTERVAL '7 days') > 0
            ORDER BY score DESC
            LIMIT 5
        """)
        high_limit_recommended = [dict(row) for row in cur.fetchall()]
        
        # Regular Floor Statistics (all non-HD locations)
        cur.execute("""
            SELECT 
                COUNT(*) as count,
                ROUND(AVG(amount), 2) as avg_amount,
                MAX(amount) as max_amount,
                MIN(amount) as min_amount
            FROM jackpots
            WHERE (location_id NOT LIKE 'HD%' OR location_id IS NULL) 
                AND machine_name NOT ILIKE '%Poker%' AND machine_name NOT ILIKE '%Keno%'
        """)
        regular_floor_overall = dict(cur.fetchone() or {})
        
        # Recommended regular floor machines (using 7-day recency, excluding HD)
        cur.execute("""
            SELECT 
                machine_name,
                denomination,
                COUNT(*) as hit_count,
                ROUND(AVG(amount), 2) as avg_payout,
                MAX(amount) as max_payout,
                COUNT(*) FILTER (WHERE hit_timestamp > NOW() - INTERVAL '7 days') as hits_7d
            FROM jackpots
            WHERE (location_id NOT LIKE 'HD%' OR location_id IS NULL)
                AND machine_name NOT ILIKE '%Poker%' 
                AND machine_name NOT ILIKE '%Keno%'
            GROUP BY machine_name, denomination
            HAVING COUNT(*) >= 3
                AND COUNT(*) FILTER (WHERE hit_timestamp > NOW() - INTERVAL '7 days') > 0
            ORDER BY (COUNT(*) FILTER (WHERE hit_timestamp > NOW() - INTERVAL '7 days')) * AVG(amount) DESC
            LIMIT 5
        """)
        regular_floor_recommended = [dict(row) for row in cur.fetchall()]
        
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
            WHERE amount IS NOT NULL AND machine_name NOT ILIKE '%Poker%' AND machine_name NOT ILIKE '%Keno%'
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
                COUNT(*) FILTER (WHERE hit_timestamp > NOW() - INTERVAL '30 days') as hits_30d,
                MIN(hit_timestamp) as first_hit,
                ROUND(AVG(amount), 2) as avg_payout,
                denomination
            FROM jackpots
            WHERE amount IS NOT NULL AND machine_name NOT ILIKE '%Poker%' AND machine_name NOT ILIKE '%Keno%'
            GROUP BY machine_name, denomination
            ORDER BY hit_count DESC
            LIMIT 10
        """)
        top_machines = [dict(row) for row in cur.fetchall()]
        
        # Calculate trends for top machines
        for m in top_machines:
            days_active = (datetime.now() - m['first_hit']).days
            if days_active < 30: days_active = 30
            daily_avg = m['hit_count'] / days_active
            expected = daily_avg * 30
            ratio = m['hits_30d'] / expected if expected > 0 else 0
            
            if ratio > 1.2: m['color'] = '#ff6b6b' # Red (Heating Up)
            elif ratio < 0.6: m['color'] = '#4dabf7' # Blue (Slowing Down)
            else: m['color'] = '#ffffff' # White (Neutral)
        
        # Best ROI by denomination (avg payout / denomination)
        cur.execute("""
            SELECT 
                denomination,
                COUNT(*) as count,
                ROUND(AVG(amount), 2) as avg_payout,
                ROUND(MAX(amount), 2) as max_payout
            FROM jackpots
            WHERE amount IS NOT NULL AND denomination != 'Unknown' AND machine_name NOT ILIKE '%Poker%' AND machine_name NOT ILIKE '%Keno%'
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
        
        # Format best hours (Ensure all 24 hours are present)
        hours_map = {int(row['hour']): row for row in best_hours_data}
        best_hours = []
        for h in range(24):
            row = hours_map.get(h, {'hit_count': 0, 'avg_payout': 0})
            if h == 0:
                time_str = '12 AM'
            elif h < 12:
                time_str = f'{h} AM'
            elif h == 12:
                time_str = '12 PM'
            else:
                time_str = f'{h-12} PM'
            
            best_hours.append({
                'time': time_str,
                'hits': row['hit_count'],
                'avg_payout': float(row['avg_payout'] or 0),
                'hour_sort': h
            })
        
        # Sort by hits descending for the "Best Time" list
        best_hours.sort(key=lambda x: x['hits'], reverse=True)
        
        # Zone Performance (by location prefix)
        cur.execute("""
            SELECT 
                LEFT(location_id, 2) as zone, 
                COUNT(*) as hits, 
                ROUND(AVG(amount), 2) as avg_payout,
                MAX(amount) as max_payout
            FROM jackpots 
            WHERE location_id IS NOT NULL AND machine_name NOT ILIKE '%Poker%' AND machine_name NOT ILIKE '%Keno%'
            GROUP BY zone 
            ORDER BY hits DESC 
            LIMIT 6
        """)
        zones = [dict(row) for row in cur.fetchall()]
        
        # Zone Performance (Regular Floor: < $5 denom)
        cur.execute("""
            SELECT 
                LEFT(location_id, 2) as zone, 
                COUNT(*) as hits, 
                ROUND(AVG(amount), 2) as avg_payout,
                MAX(amount) as max_payout
            FROM jackpots 
            WHERE location_id IS NOT NULL AND location_id NOT LIKE 'HD%'
            AND denomination NOT IN ('$5.00', '$10.00', '$100.00')
            AND machine_name NOT ILIKE '%Poker%' AND machine_name NOT ILIKE '%Keno%'
            GROUP BY zone 
            ORDER BY hits DESC 
            LIMIT 6
        """)
        zones_regular = [dict(row) for row in cur.fetchall()]
        
        # Game Families (Group by first word or special cases)
        cur.execute("""
            SELECT 
                CASE 
                    WHEN machine_name ILIKE 'Dragon Link%' THEN 'Dragon Link'
                    WHEN machine_name ILIKE 'Dragon Cash%' THEN 'Dragon Cash'
                    WHEN machine_name ILIKE 'Lightning Link%' THEN 'Lightning Link'
                    WHEN machine_name ILIKE 'Buffalo%' THEN 'Buffalo'
                    WHEN machine_name ILIKE 'Wheel of Fortune%' THEN 'Wheel of Fortune'
                    WHEN machine_name ILIKE '%Huff%Puff%' THEN 'Huff N Puff'
                    WHEN machine_name ILIKE 'Dancing Drums%' THEN 'Dancing Drums'
                    WHEN machine_name ILIKE '88 Fortunes%' THEN '88 Fortunes'
                    WHEN machine_name ILIKE 'Lock It Link%' THEN 'Lock It Link'
                    WHEN machine_name ILIKE 'Ultimate Fire Link%' THEN 'Ultimate Fire Link'
                    WHEN machine_name ILIKE '%Top Dollar%' THEN 'Top Dollar Family'
                    WHEN machine_name ILIKE '%Pinball%' THEN 'Pinball'
                    WHEN machine_name ILIKE 'Double Diamond%' THEN 'Double Diamond'
                    WHEN machine_name ILIKE 'Double Gold%' THEN 'Double Gold'
                    WHEN machine_name ILIKE 'Triple Diamond%' THEN 'Triple Diamond'
                    ELSE split_part(machine_name, ' ', 1)
                END as family, 
                COUNT(*) as hits, 
                ROUND(AVG(amount), 2) as avg_payout
            FROM jackpots 
            WHERE amount IS NOT NULL AND machine_name NOT ILIKE '%Poker%' AND machine_name NOT ILIKE '%Keno%'
            GROUP BY family 
            ORDER BY hits DESC 
            LIMIT 12
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
            WHERE machine_name NOT ILIKE '%Poker%' AND machine_name NOT ILIKE '%Keno%'
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
            
        # Recommended machines (best combination of RECENT frequency + payout)
        # Uses 7-day window to show what's hot NOW, not historical averages
        cur.execute("""
            SELECT 
                machine_name,
                denomination,
                COUNT(*) as hit_count,
                ROUND(AVG(amount), 2) as avg_payout,
                ROUND(MAX(amount), 2) as max_payout,
                MAX(hit_timestamp) as latest_hit,
                COUNT(*) FILTER (WHERE hit_timestamp > NOW() - INTERVAL '7 days') as hits_7d,
                ROUND(COUNT(*) FILTER (WHERE hit_timestamp > NOW() - INTERVAL '7 days') * AVG(amount) / 100, 2) as score
            FROM jackpots
            WHERE amount IS NOT NULL AND machine_name NOT ILIKE '%Poker%' AND machine_name NOT ILIKE '%Keno%'
            GROUP BY machine_name, denomination
            HAVING COUNT(*) >= 3 AND COUNT(*) FILTER (WHERE hit_timestamp > NOW() - INTERVAL '7 days') > 0
            ORDER BY score DESC
            LIMIT 5
        """)
        recommended = [dict(row) for row in cur.fetchall()]
        
        # Manufacturer Analysis
        cur.execute("""
            SELECT machine_name, COUNT(*) as hits, SUM(amount) as total_payout
            FROM jackpots
            WHERE amount IS NOT NULL AND machine_name NOT ILIKE '%Poker%' AND machine_name NOT ILIKE '%Keno%'
            GROUP BY machine_name
        """)
        m_rows = cur.fetchall()
        
        m_stats = {'Aristocrat': {'hits': 0, 'total': 0}, 'Light & Wonder': {'hits': 0, 'total': 0}, 'IGT': {'hits': 0, 'total': 0}, 'Konami': {'hits': 0, 'total': 0}}
        
        for row in m_rows:
            mfg = classify_manufacturer(row['machine_name'])
            if mfg in m_stats:
                m_stats[mfg]['hits'] += row['hits']
                m_stats[mfg]['total'] += row['total_payout']
        
        manufacturers = []
        for m, s in m_stats.items():
            avg = s['total'] / s['hits'] if s['hits'] > 0 else 0
            manufacturers.append({'name': m, 'hits': s['hits'], 'total': s['total'], 'avg': avg})
        manufacturers.sort(key=lambda x: x['total'], reverse=True)
        
        # --- NEW: CLUSTER ANALYSIS ---
        cur.execute("""
            WITH Clusters AS (
                SELECT 
                    machine_name,
                    hit_timestamp,
                    count(*) OVER (
                        PARTITION BY machine_name 
                        ORDER BY hit_timestamp 
                        RANGE BETWEEN INTERVAL '3 hours' PRECEDING AND CURRENT ROW
                    ) as cluster_count,
                    amount
                FROM jackpots
                WHERE hit_timestamp > NOW() - INTERVAL '24 hours'
            )
            SELECT DISTINCT ON (machine_name)
                machine_name,
                cluster_count,
                MAX(hit_timestamp) as latest_hit,
                SUM(amount) as total_payout
            FROM Clusters 
            WHERE cluster_count >= 3
            GROUP BY machine_name, cluster_count
            ORDER BY machine_name, cluster_count DESC
        """)
        # Process manually to sort
        raw_clusters = [dict(row) for row in cur.fetchall()]
        raw_clusters.sort(key=lambda x: (x['latest_hit'], x['cluster_count']), reverse=True)
        hot_clusters = raw_clusters[:5]
        
        # --- NEW: HOT BANKS ANALYSIS ---
        cur.execute("""
            SELECT 
                LEFT(location_id, 4) as bank_id,
                COUNT(*) as hits,
                COUNT(DISTINCT machine_name) as machine_count,
                ROUND(AVG(amount), 2) as avg_payout,
                MAX(amount) as max_payout,
                MAX(hit_timestamp) as last_activity
            FROM jackpots
            WHERE location_id IS NOT NULL AND LENGTH(location_id) >= 4
            GROUP BY bank_id
            HAVING COUNT(*) >= 10
            ORDER BY hits DESC
            LIMIT 8
        """)
        hot_banks = [dict(row) for row in cur.fetchall()]
        
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
            'zones_regular': zones_regular,
            'game_families': game_families,
            'manufacturers': manufacturers,
            'cold_machines': cold_machines,
            'hot_clusters': hot_clusters,
            'hot_banks': hot_banks,
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
            },
            'regular_floor': {
                'count': regular_floor_overall.get('count', 0),
                'avg': regular_floor_overall.get('avg_amount', 0),
                'max': regular_floor_overall.get('max_amount', 0),
                'recommended': regular_floor_recommended
            }
        }
    except Exception as e:
        print(f"Error getting stats: {e}")
        return {
            'hot_areas': [], 'top_machines': [], 'top_denoms': [], 'best_machines': [],
            'total_jackpots': 0, 'recent_count': 0, 'recommended': [], 'activity_by_time': [], 'best_hours': [],
            'zones': [], 'game_families': [], 'cold_machines': [],
            'avg_jackpot': 0, 'median_jackpot': 0, 'max_jackpot': 0,
            'high_limit': {'count': 0, 'avg': 0, 'max': 0, 'best_machines': [], 'recommended': []},
            'regular_floor': {'count': 0, 'avg': 0, 'max': 0, 'recommended': []}
        }
