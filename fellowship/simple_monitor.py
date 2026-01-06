#!/usr/bin/env python3
"""
Simple Fellowship Status Monitor - No dependencies
Generates HTML status page that can be served statically or integrated into existing dashboard.
"""

import json
import subprocess
from datetime import datetime
from pathlib import Path


def check_endpoint(url):
    """Check if endpoint is up."""
    try:
        result = subprocess.run(
            ['curl', '-s', '--max-time', '3', url],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except:
        return False


def get_fellowship_status():
    """Get status of all Fellowship endpoints."""
    endpoints = {
        'Aragorn Open Web UI': 'http://192.168.1.18:8080',
        'Aragorn Ollama': 'http://192.168.1.18:11434/api/tags',
        'Aragorn Exo': 'http://192.168.1.18:8000',
        'Gandalf Dashboard': 'http://192.168.1.211:8004',
        'Gandalf Ollama': 'http://192.168.1.211:11434/api/tags',
        'Legolas Nextcloud': 'http://192.168.1.176:8083',
        'Legolas Jellyfin': 'http://192.168.1.176:8096',
    }
    
    status = {}
    for name, url in endpoints.items():
        status[name] = check_endpoint(url)
    
    return status


def generate_html_status():
    """Generate standalone HTML status page."""
    status = get_fellowship_status()
    
    html = f'''<!DOCTYPE html>
<html>
<head>
    <title>The Fellowship Status</title>
    <meta charset="utf-8">
    <meta http-equiv="refresh" content="30">
    <style>
        body {{ font-family: monospace; background: #0a0a0a; color: #0f0; padding: 20px; }}
        .status {{ margin: 10px 0; }}
        .up {{ color: #0f0; }}
        .down {{ color: #f00; }}
        h1 {{ color: #00f; }}
        .time {{ color: #888; font-size: 0.8em; }}
    </style>
</head>
<body>
    <h1>🏰 The Fellowship Status</h1>
    <div class="time">Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
    <div class="time">Auto-refresh: 30 seconds</div>
    <br>
'''
    
    for name, is_up in status.items():
        status_text = '✅ ONLINE' if is_up else '❌ OFFLINE'
        css_class = 'up' if is_up else 'down'
        html += f'    <div class="status {css_class}">{status_text} - {name}</div>\n'
    
    html += '''
</body>
</html>'''
    
    return html


def main():
    """Generate and save status page."""
    html = generate_html_status()
    
    # Save to file
    output_file = Path.home() / 'fellowship_status.html'
    output_file.write_text(html)
    print(f"✅ Status page generated: {output_file}")
    print(f"View in browser: file://{output_file}")
    
    # Also print to console
    print("\n🏰 The Fellowship Status:")
    print("=" * 50)
    status = get_fellowship_status()
    for name, is_up in status.items():
        icon = '✅' if is_up else '❌'
        print(f"{icon} {name}")


if __name__ == '__main__':
    main()
