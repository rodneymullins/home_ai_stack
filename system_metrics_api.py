"""
System Metrics API Endpoint
Add this to dashboard_api.py for system-wide metrics
"""

from config import DB_CONFIG, WEALTH_DB_CONFIG, BITNET_HOST

@app.route('/api/system-metrics')
def api_system_metrics():
    """System-wide metrics for infrastructure monitoring"""
    metrics = {}
    
    # 1. Kalshi Bot P&L
    try:
        kalshi_conn = psycopg2.connect(**DB_CONFIG)
        kal_cur = kalshi_conn.cursor()
        kal_cur.execute("SELECT COALESCE(SUM(pnl), 0), COUNT(*) FROM kalshi_trades WHERE DATE(timestamp) = CURRENT_DATE")
        result = kal_cur.fetchone()
        metrics['kalshi'] = {
            'today_pnl': float(result[0]) if result else 0,
            'today_trades': int(result[1]) if result else 0,
            'status': 'active' if result and result[1] > 0 else 'idle'
        }
        kal_cur.close()
        kalshi_conn.close()
    except Exception as e:
        metrics['kalshi'] = {'error': str(e), 'status': 'error'}
    
    # 2. BitNet API Status
    try:
        import requests
        bitnet_health = requests.get(f'{BITNET_HOST}/health', timeout=2).json()
        metrics['bitnet'] = {
            'status': bitnet_health.get('status', 'unknown'),
            'uptime': bitnet_health.get('uptime_human', 'unknown'),
            'memory_mb': bitnet_health.get('memory_usage_mb', 0)
        }
    except Exception as e:
        metrics['bitnet'] = {'status': 'down', 'error': str(e)}
    
    # 3. Net Worth Change (from Wealth Dashboard)
    try:
        wealth_conn = psycopg2.connect(**WEALTH_DB_CONFIG)
        wealth_cur = wealth_conn.cursor()
        
        # Get latest net worth
        wealth_cur.execute("""
            SELECT SUM(balance) as total
            FROM accounts 
            WHERE is_active = TRUE
        """)
        current = wealth_cur.fetchone()
        current_nw = float(current[0]) if current and current[0] else 0
        
        # Get 7 days ago
        wealth_cur.execute("""
            SELECT total_net_worth 
            FROM net_worth_snapshots 
            WHERE snapshot_date <= CURRENT_DATE - INTERVAL '7 days'
            ORDER BY snapshot_date DESC 
            LIMIT 1
        """)
        prev = wealth_cur.fetchone()
        prev_nw = float(prev[0]) if prev and prev[0] else current_nw
        
        change_7d = current_nw - prev_nw
        change_pct = (change_7d / prev_nw * 100) if prev_nw > 0 else 0
        
        metrics['net_worth'] = {
            'current': round(current_nw, 2),
            'change_7d': round(change_7d, 2),
            'change_pct': round(change_pct, 2)
        }
        
        wealth_cur.close()
        wealth_conn.close()
    except Exception as e:
        metrics['net_worth'] = {'error': str(e)}
    
    # 4. Storage Usage
    try:
        import subprocess
        
        # Hot tier (Frodo SSD)
        hot_result = subprocess.run(
            ['ssh', 'rod@frodo', 'df -h /mnt/hot-videos | tail -1'],
            capture_output=True, text=True, timeout=3
        )
        if hot_result.returncode == 0:
            parts = hot_result.stdout.split()
            metrics['storage_hot'] = {
                'used': parts[2] if len(parts) > 2 else 'unknown',
                'total': parts[1] if len(parts) > 1 else 'unknown',
                'percent': parts[4].rstrip('%') if len(parts) > 4 else '0'
            }
        
        # Cold tier (Gandalf NFS)
        cold_result = subprocess.run(
            ['df', '-h', '/mnt/nfs-gandalf'],
            capture_output=True, text=True, timeout=3
        )
        if cold_result.returncode == 0:
            parts = cold_result.stdout.split('\n')[1].split()
            metrics['storage_cold'] = {
                'used': parts[2] if len(parts) > 2 else 'unknown',
                'total': parts[1] if len(parts) > 1 else 'unknown',
                'percent': parts[4].rstrip('%') if len(parts) > 4 else '0'
            }
    except Exception as e:
        metrics['storage'] = {'error': str(e)}
    
    # 5. Database Health
    try:
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            
            # Connection count
            cur.execute("SELECT count(*) FROM pg_stat_activity WHERE datname = 'postgres'")
            connections = cur.fetchone()[0]
            
            # Database size
            cur.execute("SELECT pg_database_size('postgres') / (1024*1024*1024.0)")
            db_size_gb = round(cur.fetchone()[0], 2)
            
            # Slow queries (>1s in last hour)
            cur.execute("""
                SELECT count(*) 
                FROM pg_stat_statements 
                WHERE mean_exec_time > 1000 
                AND calls > 0
            """)
            slow_queries = cur.fetchone()[0] if conn else 0
            
            metrics['database'] = {
                'connections': connections,
                'size_gb': db_size_gb,
                'slow_queries': slow_queries,
                'status': 'healthy'
            }
            
            cur.close()
            conn.close()
    except Exception as e:
        metrics['database'] = {'status': 'error', 'error': str(e)}
    
    return jsonify({
        'metrics': metrics,
        'updated_at': datetime.now().isoformat()
    })
