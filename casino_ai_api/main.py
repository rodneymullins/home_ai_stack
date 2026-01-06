"""
Casino AI Analysis API
Powered by Gemma 3 270M on Aragorn

Provides AI-powered insights for the Casino Dashboard slot tracking application.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import httpx
from datetime import datetime
import os

app = FastAPI(
    title="Casino AI API",
    description="AI-powered slot machine analysis using Gemma 3 270M",
    version="1.0.0"
)

# Ollama endpoint
OLLAMA_BASE = os.getenv("OLLAMA_BASE", "http://localhost:11434")
MODEL_NAME = "qwen2.5-coder:7b"  # Better for structured analysis

# Import advanced analysis prompts
from analysis_prompts import (
    build_hot_cold_prompt,
    build_placement_prompt,
    build_denomination_prompt,
    build_time_patterns_prompt,
    build_cluster_prompt,
    build_forecast_prompt,
    build_competitive_prompt,
    build_volatility_prompt,
    build_correlation_prompt,
    build_roi_prompt,
    build_retention_prompt,
    build_seasonal_prompt,
)


class SlotMachine(BaseModel):
    """Slot machine data model"""
    machine_id: str
    location: str
    denomination: float
    jvi: Optional[float] = None
    win_rate: Optional[float] = None
    recent_jackpots: Optional[List[float]] = None


class AnalysisRequest(BaseModel):
    """Request for slot analysis"""
    machines: List[SlotMachine]
    analysis_type: str = "general"  # general, jackpot_pattern, performance, anomaly


class InsightResponse(BaseModel):
    """AI-generated insight"""
    summary: str
    key_findings: List[str]
    recommendations: List[str]
    confidence: float


async def call_qwen_coder(prompt: str, temperature: float = 0.2) -> str:
    """Call Qwen2.5-Coder 7B via Ollama API with generous timeout for cold starts"""
    async with httpx.AsyncClient(timeout=120.0) as client:  # Increased for model loading
        try:
            response = await client.post(
                f"{OLLAMA_BASE}/api/generate",
                json={
                    "model": MODEL_NAME,
                    "prompt": prompt,
                    "stream": False,
                    "keep_alive": "24h",  # Keep model loaded for 24 hours
                    "options": {
                        "temperature": temperature,
                        "num_predict": 512
                    }
                }
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=500, 
                    detail=f"Ollama API error: {response.text}"
                )
            
            return response.json()["response"]
        
        except httpx.ReadTimeout:
            raise HTTPException(
                status_code=504,
                detail="Model inference timeout - try again (model may be loading)"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error calling Qwen Coder: {str(e)}"
            )


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "Casino AI API",
        "model": MODEL_NAME,
        "status": "online",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/health")
async def health_check():
    """Detailed health check"""
    try:
        # Test Ollama connection
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{OLLAMA_BASE}/api/tags")
            models = response.json().get("models", [])
            qwen_available = any(MODEL_NAME in m.get("name", "") for m in models)
        
        return {
            "ollama_reachable": True,
            "qwen_coder_available": qwen_available,
            "status": "healthy" if qwen_available else "degraded"
        }
    except Exception as e:
        return {
            "ollama_reachable": False,
            "error": str(e),
            "status": "unhealthy"
        }


@app.post("/analyze/slots", response_model=InsightResponse)
async def analyze_slots(request: AnalysisRequest):
    """
    Analyze slot machine data and generate insights
    
    Analysis types:
    - general: Overall performance summary
    - jackpot_pattern: Jackpot frequency and patterns
    - performance: Machine efficiency analysis
    - anomaly: Detect unusual behavior
    - hot_cold_streaks: Identify winning/losing runs
    - optimal_placement: Best floor locations
    - denomination_analysis: Compare bet sizes
    - time_patterns: Peak performance hours/days
    - cluster_analysis: Group similar machines
    - revenue_forecast: Predict future performance
    - competitive_analysis: Compare vs floor average
    - volatility_metrics: Risk/reward profiles
    - correlation_analysis: Related performance patterns
    - roi_analysis: Investment returns
    - player_retention: Repeat-play patterns
    - seasonal_trends: Monthly/quarterly patterns
    """
    
    # Build prompt based on analysis type
    prompt_builders = {
        "jackpot_pattern": build_jackpot_prompt,
        "performance": build_performance_prompt,
        "anomaly": build_anomaly_prompt,
        "hot_cold_streaks": build_hot_cold_prompt,
        "optimal_placement": build_placement_prompt,
        "denomination_analysis": build_denomination_prompt,
        "time_patterns": build_time_patterns_prompt,
        "cluster_analysis": build_cluster_prompt,
        "revenue_forecast": build_forecast_prompt,
        "competitive_analysis": build_competitive_prompt,
        "volatility_metrics": build_volatility_prompt,
        "correlation_analysis": build_correlation_prompt,
        "roi_analysis": build_roi_prompt,
        "player_retention": build_retention_prompt,
        "seasonal_trends": build_seasonal_prompt,
    }
    
    prompt_builder = prompt_builders.get(request.analysis_type, build_general_prompt)
    prompt = prompt_builder(request.machines)
    
    # Get AI analysis
    ai_response = await call_qwen_coder(prompt, temperature=0.2)
    
    # Parse response into structured format
    insight = parse_ai_response(ai_response)
    
    return insight


def build_general_prompt(machines: List[SlotMachine]) -> str:
    """Build prompt for general analysis"""
    machine_data = []
    for m in machines[:20]:  # Limit to top 20 for context
        machine_data.append(
            f"- {m.machine_id} ({m.location}): "
            f"Denom ${m.denomination}, "
            f"JVI: {m.jvi or 'N/A'}, "
            f"Win Rate: {m.win_rate or 'N/A'}%"
        )
    
    return f"""Analyze these slot machines and provide insights:

{chr(10).join(machine_data)}

Provide:
1. A brief summary (2-3 sentences)
2. Top 3 key findings
3. Top 3 actionable recommendations

Format your response as:
SUMMARY: [your summary]
FINDINGS:
- [finding 1]
- [finding 2]
- [finding 3]
RECOMMENDATIONS:
- [rec 1]
- [rec 2]
- [rec 3]"""


def build_jackpot_prompt(machines: List[SlotMachine]) -> str:
    """Build prompt for jackpot pattern analysis"""
    jackpot_data = []
    for m in machines[:20]:
        if m.recent_jackpots:
            avg_jp = sum(m.recent_jackpots) / len(m.recent_jackpots)
            jackpot_data.append(
                f"- {m.machine_id}: {len(m.recent_jackpots)} jackpots, "
                f"avg ${avg_jp:.2f}"
            )
    
    return f"""Analyze jackpot patterns from these slot machines:

{chr(10).join(jackpot_data)}

Identify patterns and trends. Format response as:
SUMMARY: [your summary]
FINDINGS:
- [pattern 1]
- [pattern 2]
- [pattern 3]
RECOMMENDATIONS:
- [action 1]
- [action 2]
- [action 3]"""


def build_performance_prompt(machines: List[SlotMachine]) -> str:
    """Build prompt for performance analysis"""
    perf_data = []
    for m in machines[:20]:
        perf_data.append(
            f"- {m.machine_id}: JVI {m.jvi or 0:.2f}, "
            f"Win Rate {m.win_rate or 0:.1f}%"
        )
    
    return f"""Analyze performance metrics for these machines:

{chr(10).join(perf_data)}

Focus on JVI and win rate efficiency. Format response as:
SUMMARY: [your summary]
FINDINGS:
- [insight 1]
- [insight 2]
- [insight 3]
RECOMMENDATIONS:
- [optimization 1]
- [optimization 2]
- [optimization 3]"""


def build_anomaly_prompt(machines: List[SlotMachine]) -> str:
    """Build prompt for anomaly detection"""
    return f"""Review these {len(machines)} slot machines for anomalies:

{chr(10).join([f"- {m.machine_id}: JVI {m.jvi or 0}, Win Rate {m.win_rate or 0}%" for m in machines[:20]])}

Identify unusual patterns or outliers. Format response as:
SUMMARY: [your summary]
FINDINGS:
- [anomaly 1]
- [anomaly 2]
- [anomaly 3]
RECOMMENDATIONS:
- [investigation 1]
- [investigation 2]
- [investigation 3]"""


def parse_ai_response(response: str) -> InsightResponse:
    """Parse AI response into structured format"""
    lines = response.strip().split("\n")
    summary = ""
    findings = []
    recommendations = []
    
    current_section = None
    
    for line in lines:
        line = line.strip()
        if line.startswith("SUMMARY:"):
            summary = line.replace("SUMMARY:", "").strip()
            current_section = "summary"
        elif line.startswith("FINDINGS:"):
            current_section = "findings"
        elif line.startswith("RECOMMENDATIONS:"):
            current_section = "recommendations"
        elif line.startswith("-") and current_section == "findings":
            findings.append(line[1:].strip())
        elif line.startswith("-") and current_section == "recommendations":
            recommendations.append(line[1:].strip())
        elif current_section == "summary" and line:
            summary += " " + line
    
    return InsightResponse(
        summary=summary or "Analysis completed",
        key_findings=findings[:3] if findings else ["No specific findings"],
        recommendations=recommendations[:3] if recommendations else ["Continue monitoring"],
        confidence=0.85  # Default confidence for Gemma 3 270M
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8080,
        log_level="info"
    )
