"""
FunctionGemma Slot Pattern Analyzer

Uses FunctionGemma for AI-powered slot machine analysis.
Adapted from arbitrage bot for casino jackpot patterns.
"""
import requests
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta


class SlotPatternAnalyzer:
    """
    AI-powered slot machine pattern analysis using FunctionGemma.
    
    Detects hot/cold machines, patterns, anomalies, and optimal timing.
    """
    
    def __init__(self, ollama_host: str = "http://192.168.1.176:11434"):
        """
        Initialize the analyzer.
        
        Args:
            ollama_host: Ollama API endpoint (Aragorn server)
        """
        self.ollama_host = ollama_host
        self.endpoint = f"{self.ollama_host}/api/generate" # Construct the full endpoint
        self.model = "functiongemma:270m"  # Smaller, faster model for real-time analysis
        self.available = self._check_availability()
        
        # Define analysis functions for FunctionGemma
        self.functions = {
            "analyze_hot_cold": {
                "description": "Determine if slot machine is hot or cold",
                "parameters": {
                    "machine_id": "string",
                    "recent_jackpots": "list",
                    "denomination": "string",
                    "return": {
                        "hot_score": "float (0 to 1)",
                        "recommendation": "string (PLAY/MONITOR/SKIP)",
                        "confidence": "float (0 to 1)",
                        "reasoning": "string"
                    }
                }
            },
            "detect_pattern": {
                "description": "Identify jackpot patterns and trends",
                "parameters": {
                    "jackpot_times": "list of timestamps",
                    "jackpot_amounts": "list of numbers",
                    "return": {
                        "pattern_detected": "boolean",
                        "pattern_type": "string",
                        "confidence": "float (0 to 1)",
                        "description": "string"
                    }
                }
            },
            "assess_timing": {
                "description": "Optimal play timing recommendation",
                "parameters": {
                    "time_since_last_jackpot": "int (minutes)",
                    "avg_interval": "int (minutes)",
                    "recent_trend": "string",
                    "return": {
                        "timing_score": "float (0 to 1)",
                        "expected_next_hit": "string",
                        "optimal_action": "string",
                        "urgency": "string (high/medium/low)"
                    }
                }
            },
            "compare_machines": {
                "description": "Compare multiple machines to find best",
                "parameters": {
                    "machines": "list of dicts",
                    "return": {
                        "best_machine_id": "string",
                        "ranking": "list",
                        "reasoning": "string"
                    }
                }
            }
        }
    
    def _call_function(self, function_name: str, **kwargs) -> Dict:
        """Call FunctionGemma function with structured output."""
        func_def = self.functions.get(function_name)
        if not func_def:
            return {}
        
        # Build prompt for FunctionGemma
        prompt = f"""Function: {function_name}
Description: {func_def['description']}

Input:
{json.dumps(kwargs, indent=2, default=str)}

Expected output format:
{json.dumps(func_def['parameters']['return'], indent=2)}

Generate output as valid JSON:"""
        
        try:
            response = requests.post(
                self.endpoint,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "temperature": 0.3,
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                output_text = result.get("response", "{}")
                
                try:
                    return json.loads(output_text)
                except json.JSONDecodeError:
                    print(f"Warning: Invalid JSON from FunctionGemma: {output_text}")
                    return {}
            
        except Exception as e:
            print(f"Error calling FunctionGemma: {e}")
        
        return {}
    
    def analyze_hot_cold(self, machine_id: str, recent_jackpots: List[Dict],
                         denomination: str = "$1.00") -> Dict:
        """
        Analyze if machine is hot or cold.
        
        Args:
            machine_id: Unique machine identifier
            recent_jackpots: List of recent jackpots with 'amount' and 'time'
            denomination: Denomination (e.g., "$1.00")
            
        Returns:
            {
                "hot_score": 0.85,
                "recommendation": "PLAY NOW",
                "confidence": 0.78,
                "reasoning": "Above-average frequency..."
            }
        """
        return self._call_function(
            "analyze_hot_cold",
            machine_id=machine_id,
            recent_jackpots=recent_jackpots,
            denomination=denomination
        )
    
    def detect_pattern(self, jackpot_times: List[datetime],
                      jackpot_amounts: List[float]) -> Dict:
        """
        Detect patterns in jackpot history.
        
        Returns:
            {
                "pattern_detected": True,
                "pattern_type": "consistent_interval",
                "confidence": 0.82,
                "description": "Jackpots occur every 45-60 minutes"
            }
        """
        # Convert datetimes to ISO strings for JSON
        times_str = [t.isoformat() if isinstance(t, datetime) else str(t) 
                     for t in jackpot_times]
        
        return self._call_function(
            "detect_pattern",
            jackpot_times=times_str,
            jackpot_amounts=jackpot_amounts
        )
    
    def assess_timing(self, time_since_last_jackpot: int,
                     avg_interval: int, recent_trend: str = "stable") -> Dict:
        """
        Assess optimal play timing.
        
        Args:
            time_since_last_jackpot: Minutes since last jackpot
            avg_interval: Average minutes between jackpots
            recent_trend: "increasing", "decreasing", or "stable"
            
        Returns:
            {
                "timing_score": 0.75,
                "expected_next_hit": "12-18 minutes",
                "optimal_action": "Start playing now",
                "urgency": "high"
            }
        """
        return self._call_function(
            "assess_timing",
            time_since_last_jackpot=time_since_last_jackpot,
            avg_interval=avg_interval,
            recent_trend=recent_trend
        )
    
    def compare_machines(self, machines: List[Dict]) -> Dict:
        """
        Compare multiple machines and rank them.
        
        Args:
            machines: List of dicts with machine data
            
        Returns:
            {
                "best_machine_id": "12345",
                "ranking": ["12345", "67890", ...],
                "reasoning": "Machine 12345 has highest frequency..."
            }
        """
        return self._call_function(
            "compare_machines",
            machines=machines
        )
    
    def analyze_machine(self, machine_data: Dict) -> Dict:
        """
        Comprehensive analysis of a single machine.
        
        Combines multiple AI functions for complete picture.
        
        Args:
            machine_data: Dict with machine info including:
                - machine_id
                - recent_jackpots (list)
                - denomination
                - time_since_last
                - avg_interval
                
        Returns:
            Complete AI analysis with all scores and recommendations
        """
        results = {}
        
        # 1. Hot/Cold Analysis
        hot_cold = self.analyze_hot_cold(
            machine_data.get("machine_id"),
            machine_data.get("recent_jackpots", []),
            machine_data.get("denomination", "$1.00")
        )
        results["hot_cold"] = hot_cold
        
        # 2. Pattern Detection
        if machine_data.get("recent_jackpots"):
            times = [jp.get("time") for jp in machine_data["recent_jackpots"]]
            amounts = [jp.get("amount") for jp in machine_data["recent_jackpots"]]
            
            pattern = self.detect_pattern(times, amounts)
            results["pattern"] = pattern
        
        # 3. Timing Assessment
        timing = self.assess_timing(
            machine_data.get("time_since_last", 0),
            machine_data.get("avg_interval", 60),
            machine_data.get("recent_trend", "stable")
        )
        results["timing"] = timing
        
        # 4. Combined Score
        hot_score = hot_cold.get("hot_score", 0.5)
        timing_score = timing.get("timing_score", 0.5)
        pattern_confidence = results.get("pattern", {}).get("confidence", 0.5)
        
        combined_score = (hot_score * 0.5 + timing_score * 0.3 + pattern_confidence * 0.2)
        
        # 5. Overall Recommendation
        if combined_score >= 0.75 and hot_cold.get("confidence", 0) >= 0.7:
            recommendation = "PLAY NOW - High AI Confidence"
        elif combined_score >= 0.55:
            recommendation = "MONITOR - Moderate Potential"
        else:
            recommendation = "SKIP - Low Probability"
        
        results["combined_score"] = combined_score
        results["overall_recommendation"] = recommendation
        results["ai_confidence"] = max(
            hot_cold.get("confidence", 0),
            timing.get("urgency", "low") == "high" and 0.8 or 0.5
        )
        
        return results


# Quick test
if __name__ == "__main__":
    analyzer = SlotPatternAnalyzer()
    
    # Test data
    test_machine = {
        "machine_id": "BUF-12345",
        "denomination": "$1.00",
        "recent_jackpots": [
            {"amount": 2500, "time": datetime.now() - timedelta(minutes=15)},
            {"amount": 1200, "time": datetime.now() - timedelta(minutes=45)},
            {"amount": 3100, "time": datetime.now() - timedelta(minutes=90)},
        ],
        "time_since_last": 15,
        "avg_interval": 47,
        "recent_trend": "stable"
    }
    
    print("🎰 Testing FunctionGemma Slot Analyzer...")
    print(f"   Endpoint: {analyzer.endpoint}")
    print(f"   Model: {analyzer.model}")
    print("")
    
    # Test hot/cold
    result = analyzer.analyze_hot_cold(
        test_machine["machine_id"],
        test_machine["recent_jackpots"],
        test_machine["denomination"]
    )
    
    print("Hot/Cold Analysis:")
    print(json.dumps(result, indent=2))
    print("")
    
    # Full analysis
    full_results = analyzer.analyze_machine(test_machine)
    print("Complete Analysis:")
    print(json.dumps(full_results, indent=2, default=str))
