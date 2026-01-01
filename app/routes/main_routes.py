from flask import Blueprint, render_template
from datetime import datetime
from services.stats_service import get_jackpot_stats
from app.services.data_service import (
    get_trending_searches, 
    get_news, 
    get_services, 
    get_jackpots, 
    get_multi_casino_stats,
    format_time_ago
)

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    trending_us = get_trending_searches('united_states')
    trending_global = get_trending_searches('worldwide')
    news_data = get_news()
    services = get_services()
    
    jackpots_raw = get_jackpots()
    jackpots_data = []
    for jp in jackpots_raw[:100]:
        jackpots_data.append({
            'location_id': jp.get('location_id', 'Unknown'),
            'machine_name': jp.get('machine_name', 'Unknown')[:50],
            'denomination': jp.get('denomination', 'Unknown'),
            'amount': jp.get('amount'),
            'timestamp': jp.get('hit_timestamp'),
            'time_ago': format_time_ago(jp.get('hit_timestamp') or jp.get('scraped_at'))
        })
    
    # Get casino statistics
    stats = get_jackpot_stats()
    
    update_time = datetime.now().strftime('%H:%M:%S')
    
    multi_casino = get_multi_casino_stats()
    
    return render_template('dashboard.html', 
                           trending_us=trending_us, trending_global=trending_global,
                           news_data=news_data, services=services, jackpots_data=jackpots_data,
                           stats=stats, multi_casino=multi_casino, update_time=update_time)
