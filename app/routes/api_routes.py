from flask import Blueprint, jsonify, request
from app.services.data_service import get_jackpots
from app.services.analytics_service import (
    get_hourly_analytics, 
    get_jackpot_outliers,
    get_jackpot_clusters,
    get_hot_banks
)
from services.stats_service import get_jackpot_stats
from app.services.llm_service import generate_briefing, parse_search_query

api_bp = Blueprint('api', __name__)

@api_bp.route('/api/analytics')
def api_analytics():
    """API endpoint for real-time analytics updates"""
    return jsonify({
        'hourly': get_hourly_analytics(),
        'outliers': get_jackpot_outliers(),
        'clusters': get_jackpot_clusters(),
        'banks': get_hot_banks()
    })

@api_bp.route('/api/jackpots')
def api_jackpots():
    return jsonify(get_jackpots())

@api_bp.route('/api/daily-briefing')
def api_daily_briefing():
    stats = get_jackpot_stats()
    briefing = generate_briefing(stats)
    return jsonify({'briefing': briefing})

@api_bp.route('/api/smart-search')
def api_smart_search():
    query = request.args.get('q', '')
    if not query:
        return jsonify({})
    filters = parse_search_query(query)
    return jsonify(filters)
