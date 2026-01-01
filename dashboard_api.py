# JSON API endpoints for Tabler dashboard auto-refresh

@app.route('/api/high-limit-stats')
def api_high_limit_stats():
    """JSON API for high limit room stats"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database error'}), 500
    
    try:
        cur = conn.cursor()
        
        # High limit stats
        cur.execute("""
            SELECT 
                COUNT(*) as count,
                ROUND(AVG(amount), 2) as avg,
                MAX(amount) as max
            FROM jackpots
            WHERE amount >= 10000
        """)
        stats = dict(cur.fetchone() or {'count': 0, 'avg': 0, 'max': 0})
        
        # Top high-limit machines (7-day recency)
        cur.execute("""
            SELECT 
                machine_name,
                denomination,
                COUNT(*) as hit_count,
                ROUND(AVG(amount), 2) as avg_payout,
                MAX(amount) as max_payout,
                COUNT(*) FILTER (WHERE hit_timestamp > NOW() - INTERVAL '7 days') as hits_7d
            FROM jackpots
            WHERE amount >= 10000 
                AND machine_name NOT ILIKE '%Poker%' 
                AND machine_name NOT ILIKE '%Keno%'
            GROUP BY machine_name, denomination
            HAVING COUNT(*) >= 2 
                AND COUNT(*) FILTER (WHERE hit_timestamp > NOW() - INTERVAL '7 days') > 0
            ORDER BY hits_7d * AVG(amount) DESC
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
    """JSON API for regular floor stats"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database error'}), 500
    
    try:
        cur = conn.cursor()
        
        # Regular floor stats
        cur.execute("""
            SELECT 
                COUNT(*) as count,
                ROUND(AVG(amount), 2) as avg,
                MAX(amount) as max
            FROM jackpots
            WHERE amount < 10000
                AND machine_name NOT ILIKE '%Poker%'
                AND machine_name NOT ILIKE '%Keno%'
        """)
        stats = dict(cur.fetchone() or {'count': 0, 'avg': 0, 'max': 0})
        
        # Top regular floor machines
        cur.execute("""
            SELECT 
                machine_name,
                denomination,
                COUNT(*) as hit_count,
                ROUND(AVG(amount), 2) as avg_payout,
                MAX(amount) as max_payout,
                COUNT(*) FILTER (WHERE hit_timestamp > NOW() - INTERVAL '7 days') as hits_7d
            FROM jackpots
            WHERE amount < 10000
                AND machine_name NOT ILIKE '%Poker%'
                AND machine_name NOT ILIKE '%Keno%'
            GROUP BY machine_name, denomination
            HAVING COUNT(*) >= 3
                AND COUNT(*) FILTER (WHERE hit_timestamp > NOW() - INTERVAL '7 days') > 0
            ORDER BY hits_7d * AVG(amount) DESC
            LIMIT 5
        """)
        machines = [dict(row) for row in cur.fetchall()]
        
       # Area breakdown
        cur.execute("""
            SELECT
                SUBSTRING(location_id, 1, 2) as area_code,
                COUNT(*) as hit_count,
                ROUND(AVG(amount), 2) as avg_payout,
                COUNT(*) FILTER (WHERE hit_timestamp > NOW() - INTERVAL '24 hours') as hits_24h
            FROM jackpots
            WHERE amount < 10000
                AND machine_name NOT ILIKE '%Poker%'
                AND machine_name NOT ILIKE '%Keno%'
                AND location_id IS NOT NULL
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
    """JSON API for latest jackpot hits"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database error'}), 500
    
    try:
        cur = conn.cursor()
        
        cur.execute("""
            SELECT 
                machine_name,
                amount,
                denomination,
                location_id,
                hit_timestamp,
                scraped_at
            FROM jackpots
            WHERE machine_name NOT ILIKE '%Poker%'
                AND machine_name NOT ILIKE '%Keno%'
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

@app.route('/api/hot-machines')
def api_hot_machines():
    """JSON API for trending hot machines"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database error'}), 500
    
    try:
        cur = conn.cursor()
        
        # Machines heating up - based on recent vs historical frequency
        cur.execute("""
            WITH machine_recent AS (
                SELECT 
                    machine_name,
                    COUNT(*) as hits_7d,
                    ROUND(AVG(amount), 2) as avg_recent
                FROM jackpots
                WHERE hit_timestamp > NOW() - INTERVAL '7 days'
                    AND machine_name NOT ILIKE '%Poker%'
                    AND machine_name NOT ILIKE '%Keno%'
                GROUP BY machine_name
                HAVING COUNT(*) >= 3
            ),
            machine_historical AS (
                SELECT 
                    machine_name,
                    COUNT(*) / 30.0 as daily_avg_historical
                FROM jackpots
                WHERE hit_timestamp BETWEEN NOW() - INTERVAL '30 days' AND NOW() - INTERVAL '7 days'
                    AND machine_name NOT ILIKE '%Poker%'
                    AND machine_name NOT ILIKE '%Keno%'
                GROUP BY machine_name
            )
            SELECT 
                r.machine_name,
                r.hits_7d,
                r.avg_recent,
                ROUND((r.hits_7d / 7.0) / NULLIF(h.daily_avg_historical, 0), 2) as heat_ratio
            FROM machine_recent r
            LEFT JOIN machine_historical h ON r.machine_name = h.machine_name
            WHERE h.daily_avg_historical > 0
            ORDER BY heat_ratio DESC NULLS LAST
            LIMIT 10
        """)
        
        hot_machines = [dict(row) for row in cur.fetchall()]
        
        cur.close()
        conn.close()
        
        return jsonify({
            'machines': hot_machines,
            'updated_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
