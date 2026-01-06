#!/usr/bin/env python3
"""
Iframe section routes with 1-3 flame heat rating and location-based high limit detection
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

def get_heat_rating(hits_7d, hits_30d):
    """Calculate 1-3 flame heat rating based on recent activity"""
    if hits_30d == 0:
        return "🔥", "heat-1"  # Cold but has some hits
    
    weekly_rate = hits_7d / 7.0
    monthly_rate = hits_30d / 30.0
    
    # 3-flame system based on acceleration
    if weekly_rate > monthly_rate * 1.5:
        return "🔥🔥🔥", "heat-3"  # Super hot
    elif weekly_rate > monthly_rate * 1.1:
        return "🔥🔥", "heat-2"  # Hot
    else:
        return "🔥", "heat-1"  # Warm

def is_high_limit_location(location_id):
    """Determine if a location is in the high limit room based on zone prefix"""
    if not location_id:
        return False
    # Common high limit prefixes - adjust based on your casino layout
    high_limit_prefixes = ['HL', 'VIP', 'HI', 'HR']  # HL=High Limit, HR=High Roller, etc
    prefix = location_id[:2].upper()
    return prefix in high_limit_prefixes

def classify_manufacturer(machine_name):
    """Classify manufacturer from machine name"""
    name_upper = machine_name.upper()
    if 'IGT' in name_upper or 'MULTI-GAME' in name_upper:
        return 'IGT'
    elif 'ARISTOCRAT' in name_upper or 'BUFFALO' in name_upper or 'DRAGON' in name_upper:
        return 'Aristocrat'
    elif 'KONAMI' in name_upper:
        return 'Konami'
    elif 'BALLY' in name_upper:
        return 'Bally'
    elif 'AINSWORTH' in name_upper:
        return 'Ainsworth'
    return 'Unknown'

# Shared iframe styles with 3-flame heat CSS
IFRAME_STYLES = """
<link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@400;700&family=Crimson+Text:wght@400;600&display=swap" rel="stylesheet">
<style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    :root { 
        --gold: #d4af37; 
        --bronze: #cd7f32; 
        --parchment: #f4e8d0; 
        --accent: #20c997;
        --bg-dark: #1a0f0a;
        --bg-medium: #2c1810;
    }
    body { 
        font-family: 'Crimson Text', serif; 
        background: linear-gradient(135deg, var(--bg-dark), var(--bg-medium));
        color: var(--parchment); 
        padding: 10px;
        max-height: 100vh;
        overflow-y: auto;
    }
    h2, h3, h4 { 
        font-family: 'Cinzel', serif; 
        color: var(--gold); 
        text-shadow: 0 0 10px rgba(212, 175, 55, 0.3); 
    }
    .section-header {
        font-size: 1.3em;
        text-align: center;
        padding: 10px;
        background: linear-gradient(90deg, transparent, rgba(212, 175, 55, 0.2), transparent);
        border-radius: 6px;
        margin-bottom: 10px;
    }
    .stat-grid { 
        display: grid; 
        grid-template-columns: repeat(3, 1fr); 
        gap: 12px; 
        margin: 15px 0; 
    }
    .stat-box { 
        text-align: center; 
        padding: 15px; 
        background: linear-gradient(145deg, rgba(212, 175, 55, 0.15), rgba(205, 127, 50, 0.08));
        border: 1px solid rgba(212, 175, 55, 0.4);
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .stat-value { 
        font-size: 1.6em; 
        color: var(--gold); 
        font-family: 'Cinzel', serif; 
        font-weight: 700; 
        text-shadow: 0 2px 4px rgba(0,0,0,0.5);
    }
    .stat-label { 
        font-size: 0.7em; 
        color: rgba(244, 232, 208, 0.7); 
        text-transform: uppercase; 
        margin-top: 3px; 
        letter-spacing: 1px;
    }
    .machine-item { 
        padding: 12px; 
        margin: 8px 0; 
        background: linear-gradient(90deg, rgba(212, 175, 55, 0.12), rgba(205, 127, 50, 0.06)); 
        border-left: 4px solid var(--gold);
        border-radius: 4px;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    .machine-item:hover { 
        background: linear-gradient(90deg, rgba(212, 175, 55, 0.25), rgba(205, 127, 50, 0.15)); 
        transform: translateX(5px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.3);
    }
    .machine-name { 
        font-weight: 700; 
        color: var(--gold); 
        margin-bottom: 6px; 
        font-size: 0.95em; 
        text-shadow: 0 1px 2px rgba(0,0,0,0.3);
    }
    .machine-meta { 
        display: flex; 
        gap: 8px; 
        flex-wrap: wrap;
        font-size: 0.7em; 
        color: rgba(244, 232, 208, 0.8); 
        margin: 6px 0;
    }
    .meta-item {
        background: rgba(212, 175, 55, 0.15);
        padding: 3px 8px;
        border-radius: 4px;
        border: 1px solid rgba(212, 175, 55, 0.3);
        white-space: nowrap;
    }
    .machine-stats { 
        display: flex; 
        justify-content: space-between; 
        align-items: center;
        font-size: 0.85em; 
        color: rgba(244, 232, 208, 0.9); 
        margin-top: 6px; 
    }
    .machine-detail { 
        font-size: 0.75em; 
        color: rgba(244, 232, 208, 0.7); 
        margin-top: 4px; 
    }
    .heat-3 { color: #ff3333; font-size: 1.2em; text-shadow: 0 0 8px #ff3333; }
    .heat-2 { color: #ff8844; font-size: 1.1em; text-shadow: 0 0 6px #ff8844; }
    .heat-1 { color: #ffd43b; font-size: 1.0em; }
</style>
"""

def register_iframe_routes(app):
    """Register all iframe section routes"""
    
    @app.route('/section/high-limit')
    def section_high_limit():
        """High Limit Room section - Based on location zones"""
        conn = get_db_connection()
        if not conn:
            return "Database error", 500
        
        try:
            cur = conn.cursor()
            
            # High limit stats - use amount >= 10000 as proxy for high limit
            cur.execute("""
                SELECT 
                    COUNT(*) as count,
                    ROUND(AVG(amount), 2) as avg,
                    MAX(amount) as max
                FROM jackpots
                WHERE amount >= 10000
            """)
            stats = dict(cur.fetchone() or {'count': 0, 'avg': 0, 'max': 0})
            
            # Top high-limit machines
            cur.execute("""
                SELECT 
                    j.machine_name,
                    j.denomination,
                    j.location_id,
                    COUNT(*) as hit_count,
                    ROUND(AVG(j.amount), 2) as avg_payout,
                    MAX(j.amount) as max_payout,
                    COUNT(*) FILTER (WHERE j.hit_timestamp > NOW() - INTERVAL '7 days') as hits_7d,
                    COUNT(*) FILTER (WHERE j.hit_timestamp > NOW() - INTERVAL '30 days') as hits_30d,
                    s.manufacturer,
                    s.volatility
                FROM jackpots j
                LEFT JOIN slot_machines s ON j.machine_name = s.machine_name
                WHERE j.amount >= 10000
                    AND j.machine_name NOT ILIKE '%Poker%' 
                    AND j.machine_name NOT ILIKE '%Keno%'
                GROUP BY j.machine_name, j.denomination, j.location_id, s.manufacturer, s.volatility
                HAVING COUNT(*) >= 2 
                    AND COUNT(*) FILTER (WHERE j.hit_timestamp > NOW() - INTERVAL '7 days') > 0
                ORDER BY COUNT(*) FILTER (WHERE j.hit_timestamp > NOW() - INTERVAL '7 days') * AVG(j.amount) DESC
                LIMIT 50
            """)
            machines = [dict(row) for row in cur.fetchall()]
            
            # Add heat ratings and fallback manufacturer
            for m in machines:
                m['heat_text'], m['heat_class'] = get_heat_rating(m['hits_7d'], m['hits_30d'])
                if not m['manufacturer']:
                    m['manufacturer'] = classify_manufacturer(m['machine_name'])
                if not m['volatility']:
                    m['volatility'] = 'Unknown'
            
            cur.close()
            conn.close()
            
            html = """<!DOCTYPE html>
            <html>
            <head>
                <meta http-equiv="refresh" content="120">
                """ + IFRAME_STYLES + """
            </head>
            <body>
                <h3 class="section-header">👑 HIGH LIMIT ROOM</h3>
                <p style="font-size: 0.8em; color: rgba(244, 232, 208, 0.7); margin-bottom: 15px; text-align: center;">Premium Jackpots $10,000+</p>
                
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
                
                <h4 style="font-size: 0.95em; margin: 20px 0 10px 0; color: var(--gold); text-align: center;">⭐ Hottest Premium Machines</h4>
                {% for m in machines %}
                <div class="machine-item" onclick="window.parent.location.href='/machine/{{ m.machine_name }}'">
                    <div class="machine-name">{{ m.machine_name[:50] }}</div>
                    <div class="machine-meta">
                        <span class="meta-item">🏭 {{ m.manufacturer }}</span>
                        <span class="meta-item">📍 {{ m.location_id }}</span>
                        <span class="meta-item">💵 {{ m.denomination }}</span>
                        <span class="meta-item">⚡ {{ m.volatility }}</span>
                    </div>
                    <div class="machine-stats">
                        <span class="heat-{{ m.heat_class }}">{{ m.heat_text }}</span>
                        <span style="color: var(--accent); font-weight: 700;">${{ "{:,.0f}".format(m.avg_payout) }}</span>
                    </div>
                    <div class="machine-detail">📊 {{ m.hits_7d }} hits last 7d • 💎 Max: ${{ "{:,.0f}".format(m.max_payout) }}</div>
                </div>
                {% endfor %}
                
                <div style="text-align: center; margin-top: 15px; font-size: 0.75em; color: rgba(244, 232, 208, 0.5);">
                    🔄 Auto-refreshes every 2 minutes
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
                    j.machine_name,
                    j.denomination,
                    j.location_id,
                    COUNT(*) as hit_count,
                    ROUND(AVG(j.amount), 2) as avg_payout,
                    MAX(j.amount) as max_payout,
                    COUNT(*) FILTER (WHERE j.hit_timestamp > NOW() - INTERVAL '7 days') as hits_7d,
                    COUNT(*) FILTER (WHERE j.hit_timestamp > NOW() - INTERVAL '30 days') as hits_30d,
                    s.manufacturer,
                    s.volatility
                FROM jackpots j
                LEFT JOIN slot_machines s ON j.machine_name = s.machine_name
                WHERE j.amount < 10000
                    AND j.machine_name NOT ILIKE '%Poker%'
                    AND j.machine_name NOT ILIKE '%Keno%'
                GROUP BY j.machine_name, j.denomination, j.location_id, s.manufacturer, s.volatility
                HAVING COUNT(*) >= 3
                    AND COUNT(*) FILTER (WHERE j.hit_timestamp > NOW() - INTERVAL '7 days') > 0
                ORDER BY COUNT(*) FILTER (WHERE j.hit_timestamp > NOW() - INTERVAL '7 days') * AVG(j.amount) DESC
                LIMIT 50
            """)
            machines = [dict(row) for row in cur.fetchall()]
            
            # Add heat ratings and fallback manufacturer
            for m in machines:
                m['heat_text'], m['heat_class'] = get_heat_rating(m['hits_7d'], m['hits_30d'])
                if not m['manufacturer']:
                    m['manufacturer'] = classify_manufacturer(m['machine_name'])
                if not m['volatility']:
                    m['volatility'] = 'Unknown'
            
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
                <p style="font-size: 0.8em; color: rgba(244, 232, 208, 0.7); margin-bottom: 15px; text-align: center;">Main Floor Jackpots</p>
                
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
                
                <h4 style="font-size: 0.95em; margin: 20px 0 10px 0; color: var(--gold); text-align: center;">⭐ Hottest Main Floor Machines</h4>
                {% for m in machines %}
                <div class="machine-item" onclick="window.parent.location.href='/machine/{{ m.machine_name }}'">
                    <div class="machine-name">{{ m.machine_name[:50] }}</div>
                    <div class="machine-meta">
                        <span class="meta-item">🏭 {{ m.manufacturer }}</span>
                        <span class="meta-item">📍 {{ m.location_id }}</span>
                        <span class="meta-item">💵 {{ m.denomination }}</span>
                        <span class="meta-item">⚡ {{ m.volatility }}</span>
                    </div>
                    <div class="machine-stats">
                        <span class="heat-{{ m.heat_class }}">{{ m.heat_text }}</span>
                        <span style="color: var(--accent); font-weight: 700;">${{ "{:,.0f}".format(m.avg_payout) }}</span>
                    </div>
                    <div class="machine-detail">📊 {{ m.hits_7d }} hits last 7d • 💎 Max: ${{ "{:,.0f}".format(m.max_payout) }}</div>
                </div>
                {% endfor %}
                
                <div style="text-align: center; margin-top: 15px; font-size: 0.75em; color: rgba(244, 232, 208, 0.5);">
                    🔄 Auto-refreshes every 2 minutes
                </div>
            </body>
            </html>"""
            
            return render_template_string(html, machines=machines)
            
        except Exception as e:
            return f"Error: {e}", 500
    
    return app
