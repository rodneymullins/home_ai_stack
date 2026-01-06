#!/usr/bin/env python3
"""
Fellowship Dashboard - Web monitoring UI
Simple Flask dashboard for monitoring The Fellowship.
"""

from flask import Flask, render_template_string, jsonify
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fellowship.router import FellowshipRouter
from fellowship.analytics import FellowshipAnalytics
from fellowship.cache import FellowshipCache


app = Flask(__name__)
router = FellowshipRouter()
analytics = FellowshipAnalytics()
cache = FellowshipCache()

DASHBOARD_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>The Fellowship Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, SF Pro, Arial; background: #0a0a0a; color: #e0e0e0; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { font-size: 2.5em; margin-bottom: 10px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .subtitle { color: #888; margin-bottom: 30px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .card { background: #1a1a1a; border-radius: 12px; padding: 20px; border: 1px solid #333; }
        .card h2 { font-size: 1.2em; margin-bottom: 15px; color: #fff; }
        .status { display: flex; align-items: center; gap: 10px; margin: 10px 0; }
        .status-icon { width: 12px; height: 12px; border-radius: 50%; }
        .status-icon.up { background: #00ff88; box-shadow: 0 0 10px #00ff88; }
        .status-icon.down { background: #ff4444; box-shadow: 0 0 10px #ff4444; }
        .metric { font-size: 2em; font-weight: bold; color: #667eea; }
        .label { color: #888; font-size: 0.9em; text-transform: uppercase; letter-spacing: 1px; }
        .model-list { max-height: 200px; overflow-y: auto; }
        .model-item { padding: 8px; background: #111; margin: 5px 0; border-radius: 6px; font-size: 0.9em; }
        button { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; font-size: 1em; }
        button:hover { opacity: 0.9; }
        .refresh-btn { float: right; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        .loading { animation: pulse 2s infinite; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🏰 The Fellowship</h1>
        <p class="subtitle">AI Infrastructure Monitoring</p>
        
        <button class="refresh-btn" onclick="location.reload()">🔄 Refresh</button>
        
        <div class="grid" id="endpoints"></div>
        
        <div class="grid">
            <div class="card">
                <h2>📊 Usage Statistics (7 days)</h2>
                <div id="stats" class="loading">Loading...</div>
            </div>
            
            <div class="card">
                <h2>💾 Cache Status</h2>
                <div id="cache" class="loading">Loading...</div>
            </div>
        </div>
        
        <div class="card">
            <h2>🤖 Available Models</h2>
            <div id="models" class="model-list loading">Loading...</div>
        </div>
    </div>
    
    <script>
        // Load status
        fetch('/api/status')
            .then(r => r.json())
            .then(data => {
                const container = document.getElementById('endpoints');
                container.innerHTML = '';
                
                for (const [name, info] of Object.entries(data)) {
                    const card = document.createElement('div');
                    card.className = 'card';
                    card.innerHTML = `
                        <h2>${name}</h2>
                        <div class="status">
                            <span class="status-icon ${info.healthy ? 'up' : 'down'}"></span>
                            <span>${info.healthy ? '✅ Online' : '❌ Offline'}</span>
                        </div>
                        <div style="margin-top: 10px;">
                            <div class="label">Models</div>
                            <div class="metric">${info.models}</div>
                        </div>
                        <div style="margin-top: 10px; font-size: 0.9em; color: #666;">
                            Priority: ${info.priority} • ${info.url}
                        </div>
                    `;
                    container.appendChild(card);
                }
            });
        
        // Load stats
        fetch('/api/stats')
            .then(r => r.json())
            .then(data => {
                document.getElementById('stats').innerHTML = `
                    <div style="margin-bottom: 15px;">
                        <div class="label">Total Requests</div>
                        <div class="metric">${data.total_requests || 0}</div>
                    </div>
                    <div>
                        <div class="label">Failover Events</div>
                        <div class="metric">${data.failover_count || 0}</div>
                    </div>
                `;
                document.getElementById('stats').classList.remove('loading');
            });
        
        // Load cache stats
        fetch('/api/cache')
            .then(r => r.json())
            .then(data => {
                document.getElementById('cache').innerHTML = `
                    <div style="margin-bottom: 15px;">
                        <div class="label">Cached Entries</div>
                        <div class="metric">${data.total_entries}</div>
                    </div>
                    <div>
                        <div class="label">Cache Size</div>
                        <div class="metric">${data.total_size_mb.toFixed(2)} MB</div>
                    </div>
                `;
                document.getElementById('cache').classList.remove('loading');
            });
        
        // Load models
        fetch('/api/models')
            .then(r => r.json())
            .then(data => {
                const container = document.getElementById('models');
                container.innerHTML = '';
                
                for (const [endpoint, models] of Object.entries(data)) {
                    const header = document.createElement('div');
                    header.style.cssText = 'font-weight: bold; color: #667eea; margin: 10px 0 5px 0;';
                    header.textContent = endpoint;
                    container.appendChild(header);
                    
                    models.forEach(model => {
                        const item = document.createElement('div');
                        item.className = 'model-item';
                        item.textContent = model;
                        container.appendChild(item);
                    });
                }
                container.classList.remove('loading');
            });
        
        // Auto-refresh every 30 seconds
        setInterval(() => location.reload(), 30000);
    </script>
</body>
</html>
'''

@app.route('/')
def dashboard():
    """Main dashboard page."""
    return render_template_string(DASHBOARD_HTML)

@app.route('/api/status')
def api_status():
    """Get endpoint status."""
    return jsonify(router.get_status())

@app.route('/api/stats')
def api_stats():
    """Get usage statistics."""
    return jsonify(analytics.get_usage_stats(days=7))

@app.route('/api/cache')
def api_cache():
    """Get cache statistics."""
    return jsonify(cache.get_stats())

@app.route('/api/models')
def api_models():
    """Get available models."""
    return jsonify(router.list_all_models())


if __name__ == '__main__':
    print("🏰 Starting Fellowship Dashboard on http://localhost:5888")
    app.run(host='0.0.0.0', port=5888, debug=False)
