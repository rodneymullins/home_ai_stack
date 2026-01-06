#!/usr/bin/env python3
"""
Iframe section routes for auto-updating dashboard components
"""
from flask import render_template_string
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor

DB_CONFIG = {'database': 'postgres', 'user': 'rod'}

def get_db_connection():
    try:
        return psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
    except:
        return None

# Shared iframe styles
IFRAME_STYLES = """
<link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@400;700&family=Crimson+Text:wght@400;600&display=swap" rel="stylesheet">
<style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    :root { --gold: #d4af37; --bronze: #cd7f32; --parchment: #f4e8d0; --accent: #20c997; }
    body { 
        font-family: 'Crimson Text', serif; 
        background: linear-gradient(135deg, #1a0f0a, #2c1810);
        color: var(--parchment); 
        padding: 10px;
        max-height: 100vh;
        overflow-y: auto;
    }
    h2, h3, h4 { font-family: 'Cinzel', serif; color: var(--gold); text-shadow: 0 0 10px rgba(212, 175, 55, 0.3); }
    .stat-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin: 15px 0; }
    .stat-box { 
        text-align: center; 
        padding: 12px; 
        background: linear-gradient(145deg, rgba(212, 175, 55, 0.1), rgba(205, 127, 50, 0.05));
        border: 1px solid rgba(212, 175, 55, 0.3);
        border-radius: 6px;
    }
    .stat-value { font-size: 1.5em; color: var(--gold); font-family: 'Cinzel', serif; font-weight: 700; }
    .stat-label { font-size: 0.7em; color: rgba(244, 232, 208, 0.7); text-transform: uppercase; margin-top: 3px; }
    .machine-item { 
        padding: 12px; 
        margin: 8px 0; 
        background: linear-gradient(90deg, rgba(212, 175, 55, 0.12), rgba(205, 127, 50, 0.06)); 
        border-left: 4px solid var(--gold);
        border-radius: 4px;
        cursor: pointer;
        transition: all 0.3s;
    }
    .machine-item:hover { 
        background: linear-gradient(90deg, rgba(212, 175, 55, 0.25), rgba(205, 127, 50, 0.15)); 
        transform: translateX(5px);
    }
    .machine-name { font-weight: 700; color: var(--gold); margin-bottom: 5px; font-size: 0.95em; }
    .machine-stats { display: flex; justify-content: space-between; font-size: 0.85em; color: rgba(244, 232, 208, 0.9); }
    .machine-detail { font-size: 0.75em; color: rgba(244, 232, 208, 0.7); margin-top: 3px; }
</style>
"""

def register_iframe_routes(app):
    """Register all iframe section routes"""
    
    @app.route('/section/high-limit')
    def section_high_limit():
        """High Limit Room section - $10k+ jackpots"""
        conn = get_db_connection()
        if not conn:
            return "Database error", 500
        
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
                ORDER BY COUNT(*) FILTER (WHERE hit_timestamp > NOW() - INTERVAL '7 days') * AVG(amount) DESC
                LIMIT 50
            """)
            machines = [dict(row) for row in cur.fetchall()]
            
            cur.close()
            conn.close()
            
            # Build template with proper concatenation
            html = """<!DOCTYPE html>
            <html>
            <head>
                <meta http-equiv="refresh" content="120">
                """ + IFRAME_STYLES + """
            </head>
            <body>
                <h3 class="section-header">👑 HIGH LIMIT ROOM</h3>
                <p style="font-size: 0.8em; color: rgba(244, 232, 208, 0.7); margin-bottom: 15px;">Jackpots $10,000+</p>
                
                <div class="stat-grid">
                    <div class="stat-box">
                        <div class="stat-value">""" + "{:,}".format(stats['count']) + """</div>
                        <div class="stat-label">Total Hits</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value">$""" + "{:,.0f}".format(stats['avg']) + """</div>
                        <div class="stat-label">Avg Payout</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value">$""" + "{:,.0f}".format(stats['max']) + """</div>
                        <div class="stat-label">Max Hit</div>
                    </div>
                </div>
                
                <h4 style="font-size: 0.95em; margin: 20px 0 10px 0; color: var(--gold);">⭐ Hot High-Limit Machines (Last 7 Days)</h4>
                {% for m in machines %}
                <div class="machine-item" onclick="window.parent.location.href='/machine/{{ m.machine_name }}'">
                    <div class="machine-name">{{ m.machine_name[:35] }}</div>
                    <div class="machine-stats">
                        <span>{{ m.denomination }}</span>
                        <span style="color: var(--accent); font-weight: 700;">${{ "{:,.0f}".format(m.avg_payout) }}</span>
                    </div>
                    <div class="machine-detail">Location: {{ m.location_id }} • {{ m.hits_7d }} hits last week • Max: ${{ "{:,.0f}".format(m.max_payout) }}</div>
                </div>
                {% endfor %}
                
                <div style="text-align: center; margin-top: 15px; font-size: 0.75em; color: rgba(244, 232, 208, 0.5);">
                    Updates every 2 minutes
                </div>
            </body>
            </html>"""
            
            return render_template_string(html, machines=machines)
            
        except Exception as e:
            return f"Error: {e}", 500
    
    @app.route('/section/regular-floor')
    def section_regular_floor():
        """Regular Floor section - Under $10k jackpots"""
        conn = get_db_connection()
        if not conn:
            return "Database error", 500
        
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
                ORDER BY COUNT(*) FILTER (WHERE hit_timestamp > NOW() - INTERVAL '7 days') * AVG(amount) DESC
                LIMIT 50
            """)
            machines = [dict(row) for row in cur.fetchall()]
            
            cur.close()
            conn.close()
            
            html = """<!DOCTYPE html>
            <html>
            <head>
                <meta http-equiv="refresh" content="120">
                """ + IFRAME_STYLES + """
            </head>
            <body>
                <h3 class="section-header">🎰 REGULAR FLOOR</h3>
                <p style="font-size: 0.8em; color: rgba(244, 232, 208, 0.7); margin-bottom: 15px;">Jackpots under $10,000</p>
                
                <div class="stat-grid">
                    <div class="stat-box">
                        <div class="stat-value">""" + "{:,}".format(stats['count']) + """</div>
                        <div class="stat-label">Total Hits</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value">$""" + "{:,.0f}".format(stats['avg']) + """</div>
                        <div class="stat-label">Avg Payout</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value">$""" + "{:,.0f}".format(stats['max']) + """</div>
                        <div class="stat-label">Max Hit</div>
                    </div>
                </div>
                
                <h4 style="font-size: 0.95em; margin: 20px 0 10px 0; color: var(--gold);">⭐ Hot Machines (Last 7 Days)</h4>
                {% for m in machines %}
                <div class="machine-item" onclick="window.parent.location.href='/machine/{{ m.machine_name }}'">
                    <div class="machine-name">{{ m.machine_name[:35] }}</div>
                    <div class="machine-stats">
                        <span>{{ m.denomination }}</span>
                        <span style="color: var(--accent); font-weight: 700;">${{ "{:,.0f}".format(m.avg_payout) }}</span>
                    </div>
                    <div class="machine-detail">Location: {{ m.location_id }} • {{ m.hits_7d }} hits last week • Max: ${{ "{:,.0f}".format(m.max_payout) }}</div>
                </div>
                {% endfor %}
                
                <div style="text-align: center; margin-top: 15px; font-size: 0.75em; color: rgba(244, 232, 208, 0.5);">
                    Updates every 2 minutes
                </div>
            </body>
            </html>"""
            
            return render_template_string(html, machines=machines)
            
        except Exception as e:
            return f"Error: {e}", 500
    
    return app
