"""
Tabler-based jackpot dashboard with auto-refresh
Import and add to main google_trends_dashboard.py
"""

# Add these routes to google_trends_dashboard.py after line 1977

TABLER_API_ROUTES = '''
# JSON API endpoints for Tabler dashboard
@app.route('/api/high-limit-stats')
def api_high_limit_stats():
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database error'}), 500
    
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT 
                COUNT(*) as count,
                ROUND(AVG(amount), 2) as avg,
                MAX(amount) as max
            FROM jackpots
            WHERE amount >= 10000
        """)
        stats = dict(cur.fetchone() or {'count': 0, 'avg': 0, 'max': 0})
        
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
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database error'}), 500
    
    try:
        cur = conn.cursor()
        
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
'''

# Main Tabler dashboard route
TABLER_DASHBOARD_ROUTE = '''
@app.route('/jackpots')
def tabler_jackpots():
    """Modern Tabler-based jackpot dashboard with auto-refresh"""
    
    template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charsetutf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>🎰 Jackpot Dashboard - Coushatta Casino</title>
        
        <!-- Tabler CSS -->
        <link href="https://cdn.jsdelivr.net/npm/@tabler/core@latest/dist/css/tabler.min.css" rel="stylesheet"/>
        <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@400;700&display=swap" rel="stylesheet">
        
        <style>
            :root {
                --tblr-primary: #d4af37;
                --tblr-secondary: #cd7f32;
            }
            body {
                background: linear-gradient(135deg, #1a0f0a, #2c1810);
                font-family: system-ui, -apple-system, sans-serif;
            }
            .page-header {
                background: linear-gradient(135deg, rgba(212, 175, 55, 0.2), rgba(205, 127, 50, 0.1));
                border-bottom: 2px solid var(--tblr-primary);
            }
            .page-title {
                font-family: 'Cinzel', serif;
                color: var(--tblr-primary);
                text-shadow: 0 0 20px rgba(212, 175, 55, 0.5);
            }
            .card {
                background: rgba(43, 43, 43, 0.9);
                border: 1px solid rgba(212, 175, 55, 0.3);
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.5);
            }
            .card-header {
                background: linear-gradient(135deg, rgba(212, 175, 55, 0.2), rgba(205, 127, 50, 0.1));
                border-bottom: 1px solid rgba(212, 175, 55, 0.3);
            }
            .card-title {
                font-family: 'Cinzel', serif;
                color: var(--tblr-primary);
                font-weight: 700;
            }
            .text-gold { color: var(--tblr-primary) !important; }
            .machine-item {
                padding: 12px;
                margin: 8px 0;
                background: linear-gradient(90deg, rgba(212, 175, 55, 0.1), transparent);
                border-left: 3px solid var(--tblr-primary);
                border-radius: 4px;
                cursor: pointer;
                transition: all 0.3s;
            }
            .machine-item:hover {
                background: linear-gradient(90deg, rgba(212, 175, 55, 0.2), rgba(205, 127, 50, 0.1));
                transform: translateX(5px);
            }
            .area-badge {
                display: inline-block;
                padding: 4px 12px;
                background: linear-gradient(135deg, var(--tblr-primary), var(--tblr-secondary));
                color: #1a0f0a;
                border-radius: 4px;
                font-weight: 700;
                cursor: pointer;
                font-family: 'Cinzel', serif;
            }
            .jackpot-feed-item {
                padding: 10px;
                border-bottom: 1px solid rgba(212, 175, 55, 0.2);
                transition: background 0.2s;
            }
            .jackpot-feed-item:hover {
                background: rgba(212, 175, 55, 0.1);
            }
            .amount-large { color: #ff6b6b; font-weight: 700; font-size: 1.1em; }
            .amount-medium { color: #20c997; font-weight: 600; }
            .amount-small { color: #eaeaea; }
            .loading-overlay {
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.5);
                display: none;
                align-items: center;
                justify-content: center;
                z-index: 10;
            }
        </style>
    </head>
    <body>
        <div class="page">
            <!-- Header -->
            <header class="navbar navbar-expand-md navbar-dark d-print-none">
                <div class="container-xl">
                    <h1 class="navbar-brand navbar-brand-autodark d-none-navbar-horizontal pe-0 pe-md-3">
                        <span class="page-title">🎰 Jackpot Dashboard</span>
                    </h1>
                    <div class="navbar-nav flex-row order-md-last">
                        <div class="d-none d-md-flex">
                            <div class="nav-item dropdown">
                                <a href="/" class="nav-link">← Back to Main Dashboard</a>
                            </div>
                        </div>
                    </div>
                </div>
            </header>
            
            <!-- Page Content -->
            <div class="page-wrapper">
                <div class="container-xl">
                    <div class="page-header d-print-none">
                        <div class="row align-items-center">
                            <div class="col">
                                <h2 class="page-title">Coushatta Casino - Live Jackpot Monitoring</h2>
                                <div class="text-muted mt-1">Auto-updates every 30-120 seconds • <span id="last-update" class="text-gold">Loading...</span></div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="page-body">
                    <div class="container-xl">
                        <div class="row row-deck row-cards">
                            
                            <!-- High Limit Room Card -->
                            <div class="col-md-6">
                                <div class="card">
                                    <div class="card-header">
                                        <h3 class="card-title">👑 High Limit Room</h3>
                                        <div class="card-actions">
                                            <span class="badge bg-primary">$10,000+</span>
                                        </div>
                                    </div>
                                    <div class="card-body" id="high-limit-content">
                                        <div class="loading-overlay" style="display: flex;">
                                            <div class="spinner-border text-primary" role="status"></div>
                                        </div>
                                        <!-- Loaded via JS -->
                                    </div>
                                    <div class="card-footer text-muted">
                                        <small>Updates every 2 minutes</small>
                                    </div>
                                </div>
                            </div>
                            
                            <!-- Regular Floor Card -->
                            <div class="col-md-6">
                                <div class="card">
                                    <div class="card-header">
                                        <h3 class="card-title">🎰 Regular Floor</h3>
                                        <div class="card-actions">
                                            <span class="badge bg-secondary">Under $10,000</span>
                                        </div>
                                    </div>
                                    <div class="card-body" id="regular-floor-content">
                                        <div class="loading-overlay" style="display: flex;">
                                            <div class="spinner-border text-primary" role="status"></div>
                                        </div>
                                        <!-- Loaded via JS -->
                                    </div>
                                    <div class="card-footer text-muted">
                                        <small>Updates every 2 minutes</small>
                                    </div>
                                </div>
                            </div>
                            
                            <!-- Live Feed Card -->
                            <div class="col-12">
                                <div class="card">
                                    <div class="card-header">
                                        <h3 class="card-title">📡 Live Jackpot Feed</h3>
                                        <div class="card-actions">
                                            <span class="badge bg-success">Real-time</span>
                                        </div>
                                    </div>
                                    <div class="card-body" id="live-feed-content" style="max-height: 600px; overflow-y: auto;">
                                        <div class="loading-overlay" style="display: flex;">
                                            <div class="spinner-border text-primary" role="status"></div>
                                        </div>
                                        <!-- Loaded via JS -->
                                    </div>
                                    <div class="card-footer text-muted">
                                        <small>Updates every 30 seconds</small>
                                    </div>
                                </div>
                            </div>
                            
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Tabler JS -->
        <script src="https://cdn.jsdelivr.net/npm/@tabler/core@latest/dist/js/tabler.min.js"></script>
        
        <script>
            // Auto-refresh functions
            function updateHighLimit() {
                fetch('/api/high-limit-stats')
                    .then(r => r.json())
                    .then(data => {
                        const content = document.getElementById('high-limit-content');
                        content.querySelector('.loading-overlay').style.display = 'none';
                        
                        const stats = data.stats;
                        const machines = data.machines;
                        
                        let html = `
                            <div class="row mb-3">
                                <div class="col-4 text-center">
                                    <div class="h2 text-gold">${stats.count.toLocaleString()}</div>
                                    <div class="text-muted">Total Hits</div>
                                </div>
                                <div class="col-4 text-center">
                                    <div class="h2 text-gold">$${stats.avg.toLocaleString()}</div>
                                    <div class="text-muted">Avg Payout</div>
                                </div>
                                <div class="col-4 text-center">
                                    <div class="h2 text-success">$${stats.max.toLocaleString()}</div>
                                    <div class="text-muted">Max Hit</div>
                                </div>
                            </div>
                            <hr>
                            <h4 class="text-gold mb-3">⭐ Hot Machines (Last 7 Days)</h4>
                        `;
                        
                        machines.forEach(m => {
                            html += `
                                <div class="machine-item" onclick="window.location.href='/machine/${encodeURIComponent(m.machine_name)}'">
                                    <div class="fw-bold text-gold">${m.machine_name.substring(0, 35)}</div>
                                    <div class="d-flex justify-content-between mt-2">
                                        <span>${m.denomination}</span>
                                        <span class="text-success fw-bold">$${m.avg_payout.toLocaleString()}</span>
                                    </div>
                                    <div class="text-muted small mt-1">${m.hits_7d} hits last week • Max: $${m.max_payout.toLocaleString()}</div>
                                </div>
                            `;
                        });
                        
                        content.innerHTML = html;
                        updateTimestamp();
                    });
            }
            
            function updateRegularFloor() {
                fetch('/api/regular-floor-stats')
                    .then(r => r.json())
                    .then(data => {
                        const content = document.getElementById('regular-floor-content');
                        content.querySelector('.loading-overlay').style.display = 'none';
                        
                        const stats = data.stats;
                        const machines = data.machines;
                        const areas = data.areas;
                        
                        let html = `
                            <div class="row mb-3">
                                <div class="col-4 text-center">
                                    <div class="h2 text-gold">${stats.count.toLocaleString()}</div>
                                    <div class="text-muted">Total Hits</div>
                                </div>
                                <div class="col-4 text-center">
                                    <div class="h2 text-gold">$${stats.avg.toLocaleString()}</div>
                                    <div class="text-muted">Avg Payout</div>
                                </div>
                                <div class="col-4 text-center">
                                    <div class="h2 text-success">$${stats.max.toLocaleString()}</div>
                                    <div class="text-muted">Max Hit</div>
                                </div>
                            </div>
                            <hr>
                            <h4 class="text-gold mb-3">⭐ Hot Machines (Last 7 Days)</h4>
                        `;
                        
                        machines.forEach(m => {
                            html += `
                                <div class="machine-item" onclick="window.location.href='/machine/${encodeURIComponent(m.machine_name)}'">
                                    <div class="fw-bold text-gold">${m.machine_name.substring(0, 35)}</div>
                                    <div class="d-flex justify-content-between mt-2">
                                        <span>${m.denomination}</span>
                                        <span class="text-success fw-bold">$${m.avg_payout.toLocaleString()}</span>
                                    </div>
                                    <div class="text-muted small mt-1">${m.hits_7d} hits last week • Max: $${m.max_payout.toLocaleString()}</div>
                                </div>
                            `;
                        });
                        
                        html += `<hr><h4 class="text-gold mb-3">📍 Hot Areas (Last 24h)</h4><div class="row">`;
                        areas.forEach(area => {
                           html += `
                                <div class="col-6 col-md-3 mb-2">
                                    <div class="area-badge w-100 text-center" onclick="window.location.href='/area/${area.area_code}'">
                                        ${area.area_code} • ${area.hits_24h} hits<br>
                                        <small>$${area.avg_payout.toLocaleString()}</small>
                                    </div>
                                </div>
                            `;
                        });
                        html += `</div>`;
                        
                        content.innerHTML = html;
                        updateTimestamp();
                    });
            }
            
            function updateLiveFeed() {
                fetch('/api/live-feed')
                    .then(r => r.json())
                    .then(data => {
                        const content = document.getElementById('live-feed-content');
                        content.querySelector('.loading-overlay').style.display = 'none';
                        
                        let html = '';
                        data.jackpots.forEach(jp => {
                            const amountClass = jp.amount >= 10000 ? 'amount-large' : 
                                              jp.amount >= 5000 ? 'amount-medium' : 'amount-small';
                            
                            html += `
                                <div class="jackpot-feed-item" onclick="window.location.href='/machine/${encodeURIComponent(jp.machine_name)}'">
                                    <div class="row align-items-center">
                                        <div class="col-3">
                                            <div class="${amountClass}">$${jp.amount.toLocaleString()}</div>
                                        </div>
                                        <div class="col-6">
                                            <div class="fw-bold">${jp.machine_name.substring(0, 40)}</div>
                                            <div class="text-muted small">${jp.denomination} • ${jp.location_id || 'Unknown'}</div>
                                        </div>
                                        <div class="col-3 text-end">
                                            <div class="small text-muted">${new Date(jp.hit_timestamp || jp.scraped_at).toLocaleString()}</div>
                                        </div>
                                    </div>
                                </div>
                            `;
                        });
                        
                        content.innerHTML = html;
                        updateTimestamp();
                    });
            }
            
            function updateTimestamp() {
                document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
            }
            
            // Initial load
            updateHighLimit();
            updateRegularFloor();
            updateLiveFeed();
            
            // Set up auto-refresh intervals
            setInterval(updateHighLimit, 120000); // 2 minutes
            setInterval(updateRegularFloor, 120000); // 2 minutes
            setInterval(updateLiveFeed, 30000); // 30 seconds
        </script>
    </body>
    </html>
    """
    
    return render_template_string(template)
'''

print("="*60)
print("INSTRUCTIONS TO ADD TABLER DASHBOARD:")
print("="*60)
print()
print("1. Add the API routes after line 1977 in google_trends_dashboard.py")
print("2. Add the main /jackpots route after the API routes")
print("3. Test by visiting: http://192.168.1.211:8004/jackpots")
print()
print("="*60)
