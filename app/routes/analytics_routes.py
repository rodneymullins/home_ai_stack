from flask import Blueprint, render_template, request
from app.services.analytics_service import get_machine_details, get_bank_details

analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/machine/<path:machine_name>')
def machine_detail(machine_name):
    try:
        details = get_machine_details(machine_name)
        if not details:
            return "Machine not found", 404
        # Note: SHARED_STYLES not needed if template has its own styles
        return render_template('machine_detail.html', machine_name=machine_name, details=details)
    except Exception as e:
        return f"Error: {str(e)}", 500

@analytics_bp.route('/bank/<bank_id>')
def bank_details(bank_id):
    try:
        details = get_bank_details(bank_id)
        if not details:
            return f"Bank {bank_id} not found", 404
        return render_template('bank_detail.html', details=details)
    except Exception as e:
        return f"Error: {str(e)}", 500
