"""
Add these endpoints to casino_ai_api/main.py

Insert after line 190 (after existing analyze_slots endpoint)
"""

# Add these imports at top of file:
# import sys
# sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# from casino_ai.ai_integration import CasinoAIEngine

# Initialize AI engine (add after app creation):
# try:
#     ai_engine = CasinoAIEngine()
#     AI_MACHINE_LEARNING = True
# except Exception as e:
#     print(f"⚠️ ML Engine disabled: {e}")
#     AI_MACHINE_LEARNING = False

# Add these endpoints:

@app.get("/ai/machine/{machine_id}")
async def analyze_machine_ai(machine_id: str):
    """
    Get complete AI analysis for a specific machine.
    
    Combines FunctionGemma pattern analysis with ML predictions.
    """
    if not AI_MACHINE_LEARNING:
        raise HTTPException(status_code=503, detail="ML engine not available")
    
    try:
        result = ai_engine.analyze_machine_complete(machine_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/ai/hot-machines")
async def get_hot_machines_ai(top_n: int = 20, min_score: float = 0.6):
    """
    Get list of currently hot machines based on AI+ML analysis.
    
    Query params:
        - top_n: Number of machines to return (default 20)
        - min_score: Minimum combined score 0-1 (default 0.6)
    """
    if not AI_MACHINE_LEARNING:
        raise HTTPException(status_code=503, detail="ML engine not available")  
    
    try:
        machines = ai_engine.get_hot_machines(top_n=top_n)
        filtered = [m for m in machines if m.get('combined_score', 0) >= min_score]
        
        return {
            "count": len(filtered),
            "machines": filtered,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ai/train")
async def train_ml_models():
    """
    Train/retrain ML models on latest jackpot data.
    
    This will:
    1. Load all jackpots from PostgreSQL
    2. Engineer features
    3. Train Random Forest models
    4. Save models to models/
    """
    if not AI_MACHINE_LEARNING:
        raise HTTPException(status_code=503, detail="ML engine not available")
    
    try:
        success = ai_engine.train_models()
        
        return {
            "success": success,
            "message": "Models trained successfully" if success else "Training failed",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/ai/status")
async def ai_ml_status():
    """Get AI/ML system status"""
    return {
        "ml_engine_enabled": AI_MACHINE_LEARNING,
        "ml_models_trained": ai_engine.ml_predictor.is_trained if AI_MACHINE_LEARNING else False,
        "functiongemma_available": AI_MACHINE_LEARNING,
        "qwen_coder_available": True,  # Existing
        "endpoints": {
            "machine_analysis": "/ai/machine/{machine_id}",
            "hot_machines": "/ai/hot-machines",
            "train_models": "/ai/train",
            "status": "/ai/status"
        },
        "timestamp": datetime.utcnow().isoformat()
    }
