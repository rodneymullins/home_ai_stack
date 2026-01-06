#!/usr/bin/env python3
"""
Add a volatility recommendations route to the dashboard.
This will be inserted into google_trends_dashboard.py
"""

VOLATILITY_ROUTE = '''
@app.route('/volatility/<tier>')
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
            GROUP BY m.machine_name, m.manufacturer, m.denomination, m.volatility
            HAVING COUNT(j.id) > 5
            ORDER BY COUNT(j.id) DESC
            LIMIT 50
        """)
        
        machines = cur.fetchall()
        cur.close()
        conn.close()
        
        template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>{{ title }}</title>
            {{ styles|safe }}
        </head>
        <body>
            <div class="container">
                <a href="/" style="font-size: 1.1em; margin-bottom: 20px; display: inline-block;">← Back to Dashboard</a>
                
                <h1 class="mb-2 text-center">{{ title }}</h1>
                <p class="text-center" style="color: #888; margin-bottom: 30px;">{{ desc }}</p>
                
                <div class="card p-4">
                    <div class="table-responsive">
                        <table class="table table-dark table-hover align-middle">
                            <thead>
                                <tr style="color: var(--text-gold); border-bottom: 2px solid #555;">
                                    <th>Machine Name</th>
                                    <th>Manufacturer</th>
                                    <th>Denom</th>
                                    <th>Volatility</th>
                                    <th>Hit Count</th>
                                    <th>Avg Payout</th>
                                    <th>Max Payout</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for m in machines %}
                                <tr style="cursor: pointer;" onclick="window.location.href='/machine/{{ m.machine_name|urlencode }}'">
                                    <td><strong>{{ m.machine_name }}</strong></td>
                                    <td>{{ m.manufacturer }}</td>
                                    <td>{{ m.denomination }}</td>
                                    <td>{{ m.volatility.split('View')[0] if 'View' in m.volatility else m.volatility }}</td>
                                    <td>{{ "{:,}".format(m.hit_count) }}</td>
                                    <td>${{ "{:,.2f}".format(m.avg_payout) }}</td>
                                    <td>${{ "{:,.2f}".format(m.max_payout) }}</td>
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
        
        return render_template_string(template, machines=machines, title=title, desc=desc, styles=SHARED_STYLES)
        
    except Exception as e:
        return f"Error: {e}", 500
'''

print("Route code ready for insertion:")
print(VOLATILITY_ROUTE)
