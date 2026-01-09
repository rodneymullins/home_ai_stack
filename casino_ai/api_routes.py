"""
Casino AI API Endpoints

Add to existing casino_ai_api/main.py to integrate AI analysis.
"""
from flask import jsonify, request
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from casino_ai.ai_integration import CasinoAIEngine

# Initialize AI engine (global)
try:
    ai_engine = CasinoAIEngine()
    AI_ENABLED = True
    print("✅ Casino AI Engine initialized")
except Exception as e:
    print(f"⚠️  AI Engine disabled: {e}")
    AI_ENABLED = False
    ai_engine = None


def register_ai_routes(app):
    """Register AI analysis routes with Flask app"""
    
    @app.route('/api/ai/analyze/<machine_id>')
    def analyze_machine(machine_id):
        """
        Get complete AI analysis for a specific machine.
        
        Returns:
            JSON with AI scores, ML predictions, and recommendations
        """
        if not AI_ENABLED:
            return jsonify({"error": "AI system not available"}), 503
        
        try:
            result = ai_engine.analyze_machine_complete(machine_id)
            return jsonify(result)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/ai/hot-machines')
    def get_hot_machines():
        """
        Get list of currently hot machines.
        
        Query params:
            - top_n: Number of machines to return (default 20)
            - min_score: Minimum combined score (default 0.6)
        """
        if not AI_ENABLED:
            return jsonify({"error": "AI system not available"}), 503
        
        try:
            top_n = request.args.get('top_n', 20, type=int)
            min_score = request.args.get('min_score', 0.6, type=float)
            
            machines = ai_engine.get_hot_machines(top_n=top_n)
            
            # Filter by minimum score
            filtered = [m for m in machines if m.get('combined_score', 0) >= min_score]
            
            return jsonify({
                "count": len(filtered),
                "machines": filtered
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/ai/train', methods=['POST'])
    def train_models():
        """
        Train/retrain ML models on latest data.
        
        Returns:
            Training results and model stats
        """
        if not AI_ENABLED:
            return jsonify({"error": "AI system not available"}), 503
        
        try:
            success = ai_engine.train_models()
            
            return jsonify({
                "success": success,
                "message": "Models trained successfully" if success else "Training failed"
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/ai/status')
    def ai_status():
        """Get AI system status"""
        return jsonify({
            "enabled": AI_ENABLED,
            "ml_trained": ai_engine.ml_predictor.is_trained if AI_ENABLED else False,
            "functiongemma_available": AI_ENABLED,
            "endpoints": [
                "/api/ai/analyze/<machine_id>",
                "/api/ai/hot-machines",
                "/api/ai/train",
                "/api/ai/status"
            ]
        })
    
    print("✅ AI routes registered")


# Usage in main.py:
# from casino_ai_routes import register_ai_routes
# register_ai_routes(app)
