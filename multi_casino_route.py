@app.route('/multi-casino')
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
        
        template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Multi-Casino Jackpots</title>
            {{ styles|safe }}
        </head>
        <body>
            <div class="container">
                <a href="/" style="font-size: 1.1em; margin-bottom: 20px; display: inline-block;">← Back to Dashboard</a>
                
                <h1 class="text-center mb-4">🎰 Multi-Casino Jackpots 🎰</h1>
                <p class="text-center" style="color: #888; margin-bottom: 30px;">Latest jackpots from 7 casino properties</p>
                
                <div class="card p-4">
                    <div class="table-responsive">
                        <table class="table table-dark table-hover">
                            <thead>
                                <tr style="color: var(--text-gold); border-bottom: 2px solid #555;">
                                    <th>Casino</th>
                                    <th>Machine/Game</th>
                                    <th>Amount</th>
                                    <th>Date</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for jp in jackpots %}
                                <tr>
                                    <td><strong>{{ jp.casino }}</strong></td>
                                    <td>{{ jp.machine_name }}</td>
                                    <td style="color: var(--accent);">${{ "{:,.2f}".format(jp.amount) if jp.amount else "N/A" }}</td>
                                    <td>{{ jp.scraped_at.strftime('%m/%d %I:%M %p') if jp.scraped_at else jp.date_text or 'N/A' }}</td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>
                
                <p class="text-center mt-4" style="color: #666; font-size: 0.9em;">
                    Updated every 15 minutes • Total: {{ jackpots|length }} jackpots
                </p>
            </div>
        </body>
        </html>
        """
        
        return render_template_string(template, jackpots=jackpots, styles=SHARED_STYLES)
        
    except Exception as e:
        return f"Error: {e}", 500
