#!/usr/bin/env python3
"""
Script to add Tabler dashboard routes to google_trends_dashboard.py
Run this to integrate the new dashboard
"""
import sys

def add_tabler_routes():
    print("Adding Tabler dashboard routes to google_trends_dashboard.py...")
    
    with open('google_trends_dashboard.py', 'r') as f:
        lines = f.readlines()
    
    # Find the line after @app.route('/api/jackpots')
    insert_line = None
    for i, line in enumerate(lines):
        if "@app.route('/api/jackpots')" in line:
            # Skip to after the function def
            for j in range(i+1, min(i+10, len(lines))):
                if lines[j].strip().startswith('return') or lines[j].strip() == '':
                    insert_line = j + 1
                    break
            break
    
    if insert_line is None:
        print("Error: Could not find insertion point")
        return False
    
    # Read the API code
    with open('TABLER_DASHBOARD_CODE.py', 'r') as f:
        content = f.read()
    
    # Extract and clean API routes
    api_start = content.find("@app.route('/api/high-limit-stats')")
    api_end = content.find("@app.route('/api/live-feed')") 
    api_routes_end = content.find("'''", api_end)
    
    api_code = content[api_start:api_routes_end].strip()
    
    # Extract dashboard route
    dash_start = content.find("@app.route('/jackpots')")
    dash_end = content.rfind("'''")
    dash_code = content[dash_start:dash_end].strip()
    
    # Insert the code
    newcode = f"\n\n# Tabler Dashboard API Routes\n{api_code}\n\n# Tabler Dashboard Route\n{dash_code}\n\n"
    
    lines.insert(insert_line, newcode)
    
    # Write back
    with open('google_trends_dashboard.py', 'w') as f:
        f.writelines(lines)
    
    print("✅ Successfully added Tabler dashboard!")
    print("📊 Access at: http://192.168.1.211:8004/jackpots")
    print()
    print("Next steps:")
    print("1. scp google_trends_dashboard.py rod@192.168.1.211:/home/rod/home_ai_stack/")
    print("2. ssh rod@192.168.1.211 'sudo systemctl restart google-trends.service'")
    return True

if __name__ == "__main__":
    if add_tabler_routes():
        sys.exit(0)
    else:
        sys.exit(1)
