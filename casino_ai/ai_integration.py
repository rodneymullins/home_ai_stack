"""
Casino AI Integration Module

Combines FunctionGemma and ML for comprehensive machine analysis.
API endpoints for dashboard integration.
"""
from casino_ai.slot_pattern_analyzer import SlotPatternAnalyzer
from casino_ai.jackpot_predictor import JackpotPredictor
from typing import Dict, List
import psycopg2


class CasinoAIEngine:
    """
    Complete AI analysis engine for casino slots.
    
    Combines FunctionGemma pattern analysis with ML predictions.
    """
    
    def __init__(self):
        self.pattern_analyzer = SlotPatternAnalyzer()
        self.ml_predictor = JackpotPredictor()
        
        # Try to load trained models
        if not self.ml_predictor.is_trained:
            print("⚠️  ML models not trained. Run train_models() first.")
    
    def analyze_machine_complete(self, machine_id: str) -> Dict:
        """
        Complete AI analysis of a machine.
        
        Combines:
        - FunctionGemma pattern detection
        - ML timing prediction
        - ML hot/cold classification
        
        Returns comprehensive analysis dict.
        """
        # Fetch machine data from database
        machine_data = self._fetch_machine_data(machine_id)
        
        if not machine_data:
            return {"error": "Machine not found"}
        
        # FunctionGemma Analysis
        ai_analysis = self.pattern_analyzer.analyze_machine(machine_data)
        
        # ML Prediction
        ml_prediction = self.ml_predictor.predict(machine_data)
        
        # Combine results
        result = {
            "machine_id": machine_id,
            "timestamp": str(datetime.now()),
            
            # FunctionGemma Results
            "ai_hot_score": ai_analysis.get("hot_cold", {}).get("hot_score", 0),
            "ai_recommendation": ai_analysis.get("overall_recommendation", "UNKNOWN"),
            "ai_reasoning": ai_analysis.get("hot_cold", {}).get("reasoning", ""),
            "ai_confidence": ai_analysis.get("ai_confidence", 0),
            
            # Pattern Detection
            "pattern_detected": ai_analysis.get("pattern", {}).get("pattern_detected", False),
            "pattern_type": ai_analysis.get("pattern", {}).get("pattern_type", "none"),
            
            # Timing Assessment
            "timing_score": ai_analysis.get("timing", {}).get("timing_score", 0),
            "expected_next_hit": ai_analysis.get("timing", {}).get("expected_next_hit", "unknown"),
            
            # ML Results
            "ml_predicted_minutes": ml_prediction.get("predicted_minutes"),
            "ml_hot_probability": ml_prediction.get("hot_probability", 0),
            "ml_classification": ml_prediction.get("classification", "UNKNOWN"),
            "ml_confidence": ml_prediction.get("confidence", 0),
            
            # Combined Recommendation
            "combined_score": self._calculate_combined_score(ai_analysis, ml_prediction),
            "final_recommendation": self._get_final_recommendation(ai_analysis, ml_prediction)
        }
        
        return result
    
    def _fetch_machine_data(self, machine_id: str) -> Dict:
        """Fetch machine data from PostgreSQL"""
        try:
            from casino_ai_api.casino_data_fetcher import fetch_jackpot_history, get_db_connection
            
            # Get recent jackpots for this machine
            jackpots = fetch_jackpot_history(machine_name=machine_id, days=30)
            
            if not jackpots:
                return None
            
            # Calculate statistics
            from datetime import datetime, timedelta
            
            now = datetime.now()
            last_jackpot = jackpots[0]['date_won'] if jackpots else now
            time_since_last = (now - last_jackpot).total_seconds() / 60  # minutes
            
            # Calculate intervals
            intervals = []
            for i in range(len(jackpots) - 1):
                interval = (jackpots[i]['date_won'] - jackpots[i+1]['date_won']).total_seconds() / 60
                intervals.append(interval)
            
            avg_interval = sum(intervals) / len(intervals) if intervals else 60
            variance = np.std(intervals) if len(intervals) > 1 else 15
            
            # Get denomination (from database or assume)
            denomination = "$1.00"  # Could query from slot_machines table
            
            # Build machine data dict
            machine_data = {
                "machine_id": machine_id,
                "recent_jackpots": [
                    {"amount": jp['amount'], "time": jp['date_won']}
                    for jp in jackpots[:10]
                ],
                "time_since_last": int(time_since_last),
                "avg_interval": int(avg_interval),
                "jackpot_variance": variance,
                "denomination": denomination,
                "game_family": machine_id.split('-')[0] if '-' in machine_id else "Unknown",
                "hour_of_day": now.hour,
                "day_of_week": now.weekday(),
                "total_jackpots_today": sum(1 for jp in jackpots if jp['date_won'].date() == now.date()),
                "price_point": float(denomination.replace('$', '').replace(',', '')),
                "recent_trend": "stable"  # Could calculate from intervals
            }
            
            return machine_data
            
        except Exception as e:
            print(f"Error fetching machine data: {e}")
            return None
    
    def _calculate_combined_score(self, ai_analysis: Dict, ml_prediction: Dict) -> float:
        """Combine AI and ML scores"""
        ai_score = ai_analysis.get("combined_score", 0.5)
        ml_hot_prob = ml_prediction.get("hot_probability", 0.5)
        
        # Weight: 60% ML (trained on data), 40% AI (pattern recognition)
        combined = ai_score * 0.4 + ml_hot_prob * 0.6
        
        return combined
    
    def _get_final_recommendation(self, ai_analysis: Dict, ml_prediction: Dict) -> str:
        """Get final recommendation combining AI + ML"""
        combined_score = self._calculate_combined_score(ai_analysis, ml_prediction)
        
        ml_class = ml_prediction.get("classification", "UNKNOWN")
        ai_rec = ai_analysis.get("overall_recommendation", "")
        
        # If both agree on HOT/PLAY, high confidence
        if combined_score >= 0.75 and (ml_class == "HOT" or "PLAY" in ai_rec):
            return "🔥 PLAY NOW - High Confidence"
        elif combined_score >= 0.55:
            return "⚠️ MONITOR - Moderate Potential"  
        else:
            return "❄️ SKIP - Low Probability"
    
    def train_models(self):
        """Train ML models on database"""
        print("🎓 Training ML models on casino database...")
        success = self.ml_predictor.train()
        
        if success:
            print("✅ Models trained and saved!")
        else:
            print("❌ Training failed")
        
        return success
    
    def get_hot_machines(self, top_n: int = 10) -> List[Dict]:
        """
        Get list of currently hot machines.
        
        Returns list sorted by combined AI+ML score.
        """
        # TODO: Query database for all active machines
        # For now, return placeholder
        return []


from datetime import datetime
import numpy as np


# Quick test
if __name__ == "__main__":
    engine = CasinoAIEngine()
    
    print("🎰 Casino AI Engine - Integration Test")
    print("="*50)
    
    # Train models if needed
    if not engine.ml_predictor.is_trained:
        print("\n📊 Training ML models...")
        engine.train_models()
    
    # Test analysis on a machine
    test_machine_id = "Buffalo Grand"  # Replace with actual machine ID
    
    print(f"\n🔍 Analyzing machine: {test_machine_id}")
    result = engine.analyze_machine_complete(test_machine_id)
    
    print("\n📊 Results:")
    print(json.dumps(result, indent=2, default=str))
