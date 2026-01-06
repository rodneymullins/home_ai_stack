from flask import Blueprint, render_template, request, jsonify
from app.services.analytics_service import get_machine_details, get_bank_details
from utils.db_pool import get_db_connection
from psycopg2.extras import RealDictCursor
from app import cache

# Try importing analytics engine (assuming it's in path)

try:
    from analytics_engine import detect_hot_streaks, calculate_machine_roi, analyze_manufacturer_performance, get_game_family_insights, find_best_playing_times
    ANALYTICS_AVAILABLE = True
except ImportError:
    ANALYTICS_AVAILABLE = False
    print("Warning: analytics_engine not found")

# Try importing JVI ML
JVI_AVAILABLE = False
try:
    import sys
    import os
    # Ensure root is in path
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)
    from jvi_ml import get_ml_enhanced_rankings, load_models
    JVI_AVAILABLE = True
except ImportError:
    print("Warning: jvi_ml module not found")

analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/analytics/machine-performance')
@cache.cached(timeout=300)  # Cache for 5 minutes
def machine_performance():
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
        
        return render_template('analytics/machine_performance.html', 
                             hot_machines=hot_machines, 
                             roi_data=roi_data)
                             
    except Exception as e:
        print(f"Error in machine_performance: {e}")
        return f"Error: {str(e)}", 500

@analytics_bp.route('/machine/<path:machine_name>')
def machine_detail(machine_name):
    try:
        details = get_machine_details(machine_name)
        if not details:
            return "Machine not found", 404
        # Note: SHARED_STYLES not needed if template has its own styles
        return render_template('machine_detail.html', machine_name=machine_name, details=details)
    except Exception as e:
        return f"Error: {str(e)}", 500

@analytics_bp.route('/bank/<bank_id>')
def bank_details(bank_id):
    try:
        details = get_bank_details(bank_id)
        if not details:
            return f"Bank {bank_id} not found", 404
        return render_template('bank_detail.html', details=details)
    except Exception as e:
        return f"Error: {str(e)}", 500

@analytics_bp.route('/analytics/jvi-rankings')
@cache.cached(timeout=300)  # Cache for 5 minutes
def jvi_rankings():
    """JVI (Jackpot Value Index) rankings - ML-enhanced balanced machine scoring"""
    if not ANALYTICS_AVAILABLE:
        return "Analytics engine not available", 500
    
    try:
        # Import ML module
        import sys
        import os
        # Ensure root is in path
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if root_dir not in sys.path:
            sys.path.insert(0, root_dir)

        try:
            from jvi_ml import get_ml_enhanced_rankings, load_models
        except ImportError:
             return "JVI ML module not found", 500

        # Load ML models
        load_models()
        
        # Get ML-enhanced rankings for each mode
        jvi_balanced = get_ml_enhanced_rankings(limit=20, sort_by='balanced')
        jvi_big = get_ml_enhanced_rankings(limit=20, sort_by='big')
        jvi_fast = get_ml_enhanced_rankings(limit=20, sort_by='fast')
        
        # Get per-denomination stats
        conn = get_db_connection()
        denom_stats = []
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
        
        return render_template('analytics/jvi_rankings.html', 
                             jvi_balanced=jvi_balanced, 
                             jvi_big=jvi_big,
                             jvi_fast=jvi_fast, 
                             denom_stats=denom_stats)
        
    except Exception as e:
        print(f"Error in jvi_rankings: {e}")
        return f"Error: {str(e)}<br><br>Make sure jvi_ml.py is deployed and models are trained.", 500

@analytics_bp.route('/analytics/player-patterns')
@cache.cached(timeout=300)  # Cache for 5 minutes
def player_patterns():
    """Player pattern analytics - temporal analysis"""
    if not ANALYTICS_AVAILABLE:
        return "Analytics engine not available", 500
    
    try:
        # Import needed function from engine
        from analytics_engine import find_best_playing_times
        from app.services.analytics_service import get_weekend_stats
        
        # Get hourly patterns
        hourly_data = find_best_playing_times()
        
        # Get weekend vs weekday stats
        weekend_data = get_weekend_stats()
        
        return render_template('analytics/player_patterns.html', 
                             hourly_data=hourly_data,
                             weekend_data=weekend_data)
        
    except Exception as e:
        print(f"Error in player_patterns: {e}")
        return f"Error: {str(e)}", 500

@analytics_bp.route('/analytics/manufacturer-wars')
@cache.cached(timeout=600)  # Cache for 10 minutes
def manufacturer_wars():
    """Manufacturer comparison analytics"""
    if not ANALYTICS_AVAILABLE:
        return "Analytics engine not available", 500
    
    try:
        from analytics_engine import analyze_manufacturer_performance
        manufacturers = analyze_manufacturer_performance()
        
        return render_template('analytics/manufacturer_wars.html', manufacturers=manufacturers)
        
    except Exception as e:
        print(f"Error in manufacturer_wars: {e}")
        return f"Error: {str(e)}", 500

@analytics_bp.route('/analytics/game-families')
def game_families():
    """Game family insights"""
    if not ANALYTICS_AVAILABLE:
        return "Analytics engine not available", 500
    
    try:
        from analytics_engine import get_game_family_insights
        families = get_game_family_insights()
        
        return render_template('analytics/game_families.html', families=families)
        
    except Exception as e:
        print(f"Error in game_families: {e}")
        return f"Error: {str(e)}", 500

@analytics_bp.route('/analytics/cluster-visualization')
def cluster_visualization():
    """Interactive cluster visualization with Plotly.js"""
    if not JVI_AVAILABLE:
        return "JVI ML engine not available", 500
    
    try:
        # Load ML models
        load_models()
        
        # Get ML-enhanced rankings
        rankings = get_ml_enhanced_rankings(limit=100, sort_by='balanced')
        
        return render_template('analytics/cluster_visualization.html', rankings=rankings)
        
    except Exception as e:
        print(f"Error in cluster_visualization: {e}")
        return f"Error: {str(e)}", 500

@analytics_bp.route('/analytics/cluster-trends')
def cluster_trends():
    """Track cluster membership changes over time"""
    try:
        conn = get_db_connection()
        if not conn:
            return "Database error", 500
        
        # Get cluster history
        import pandas as pd
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
            return "No cluster history data yet. Run a snapshot first. Go to Cluster Visualization to save one.", 400
        
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
            
        return render_template('analytics/cluster_trends.html', traces=traces)
        
    except Exception as e:
        print(f"Error in cluster_trends: {e}")
        return f"Error: {str(e)}", 500

@analytics_bp.route('/analytics/save-cluster-snapshot', methods=['POST'])
def save_cluster_snapshot():
    """Save current cluster state to history"""
    if not JVI_AVAILABLE:
        return "JVI ML engine not available", 500
        
    try:
        load_models()
        rankings = get_ml_enhanced_rankings(limit=1000, sort_by='balanced')
        
        conn = get_db_connection()
        if not conn:
            return "Database error", 500
            
        cur = conn.cursor()
        
        # Create table if not exists (migrated from google_trends_dashboard.py)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cluster_history (
                id SERIAL PRIMARY KEY,
                snapshot_date DATE DEFAULT CURRENT_DATE,
                machine_name TEXT,
                cluster_label TEXT,
                jvi_score DECIMAL,
                UNIQUE(snapshot_date, machine_name)
            )
        """)
        
        # Save snapshot
        import datetime
        today = datetime.date.today()
        
        count = 0
        for r in rankings:
            cluster = r.get('ml_cluster', 'Balanced')
            jvi = r.get('jvi_balanced', 0)
            
            cur.execute("""
                INSERT INTO cluster_history (snapshot_date, machine_name, cluster_label, jvi_score)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (snapshot_date, machine_name) 
                DO UPDATE SET cluster_label = EXCLUDED.cluster_label, jvi_score = EXCLUDED.jvi_score
            """, (today, r['machine_name'], cluster, jvi))
            count += 1
            
        conn.commit()
        conn.close()
        
        return f"Snapshot saved for {count} machines. <a href='/analytics/cluster-trends'>View Trends</a>"
        
    except Exception as e:
        print(f"Error saving snapshot: {e}")
        return f"Error: {str(e)}", 500

@analytics_bp.route('/best-times')
def best_times_detail():
    """Analysis of best times to play based on hourly jackpot history"""
    from app.services.analytics_service import get_hourly_details
    hourly_data = get_hourly_details()
    if not hourly_data:
        return "Error loading data", 500
    
    return render_template('analytics/best_times.html', data=hourly_data)

@analytics_bp.route('/jackpot-forecast')
def jackpot_forecast():
    """30-day jackpot forecast using Prophet"""
    try:
        try:
            from prophet import Prophet
        except ImportError:
            return "Prophet module not installed. Please install prophet.", 500
            
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
        
        return render_template('analytics/jackpot_forecast.html', forecast_data=forecast_data)
        
    except Exception as e:
        import traceback
        print(f"Forecast error: {e}")
        return f"Forecast error: {str(e)}", 500
