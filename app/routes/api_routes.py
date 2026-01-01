from flask import Blueprint, jsonify
from app.services.data_service import get_jackpots
from app.services.analytics_service import (
    get_hourly_analytics, 
    get_jackpot_outliers,
    get_jackpot_clusters,
    get_hot_banks
)

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
