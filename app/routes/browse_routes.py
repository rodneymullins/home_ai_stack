from flask import Blueprint, render_template
from app.services.browse_service import get_group_details, get_all_machine_stats
from utils.db_pool import get_db_connection
from psycopg2.extras import RealDictCursor

browse_bp = Blueprint('browse', __name__)

@browse_bp.route('/zone/<zone_id>')
def zone_detail(zone_id):
    data = get_group_details('zone', zone_id)
    if not data:
        return "Group not found or error loading data", 404
    return render_template('browse/group_report.html', data=data, title="Zone Analysis")

@browse_bp.route('/brand/<path:brand_name>')
def brand_detail(brand_name):
    # path:brand_name allows slashes in brand name if any
    data = get_group_details('brand', brand_name)
    if not data:
        return "Brand not found or error loading data", 404
    return render_template('browse/group_report.html', data=data, title="Brand Report")

@browse_bp.route('/denom/<path:denom_value>')
def denom_detail(denom_value):
    data = get_group_details('denom', denom_value)
    if not data:
        return "Denomination not found or error loading data", 404
    return render_template('browse/group_report.html', data=data, title="Bet Size Analysis")

@browse_bp.route('/area/<area_code>')
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
        
        return render_template('browse/area_detail.html', area_code=area_code, stats=stats, machines=machines, recent_hits=recent_hits)
        
    except Exception as e:
        print(f"Error in area_detail: {e}")
        return f"Error: {str(e)}", 500

@browse_bp.route('/hottest')
def hottest_ranking():
    # Cache for this route is handled by browser/nginx or we can add decorator later
    machines = get_all_machine_stats(sort_by='hits', limit=100)
    return render_template('browse/hottest_machines.html', machines=machines)

@browse_bp.route('/volatility/<tier>')
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
                AND j.machine_name NOT ILIKE '%%Poker%%' 
                AND j.machine_name NOT ILIKE '%%Keno%%'
            GROUP BY m.machine_name, m.manufacturer, m.denomination, m.volatility
            HAVING COUNT(j.id) > 5
            ORDER BY COUNT(j.id) DESC
            LIMIT 50
        """)
        
        machines = cur.fetchall()
        cur.close()
        conn.close()
        
        return render_template('browse/volatility_recommendations.html', title=title, desc=desc, machines=machines)
        
    except Exception as e:
        print(f"Error in volatility_recommendations: {e}")
        return f"Error: {str(e)}", 500

@browse_bp.route('/payouts')
def payouts_ranking():
    machines = get_all_machine_stats()
    return render_template('browse/payouts.html', machines=machines)

@browse_bp.route('/jackpots')
def tabler_jackpots():
    """Modern Tabler-based jackpot dashboard with auto-refresh"""
    return render_template('browse/jackpots.html')

@browse_bp.route('/multi-casino')
def multi_casino():
    """Display jackpots from multiple casinos"""
    conn = get_db_connection()
    if not conn:
        return "Database error", 500
    
    try:
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
        
        return render_template('browse/multi_casino.html', jackpots=jackpots)
        
    except Exception as e:
        print(f"Error in multi_casino: {e}")
        return f"Error: {str(e)}", 500
