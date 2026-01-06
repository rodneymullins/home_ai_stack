import requests
import json
import logging

logger = logging.getLogger(__name__)

# 3-Tier Failover Configuration for High Availability
# Tier 1: M4 Mac Mini Exo (Neural Engine - fastest)
M4_EXO_URL = "http://192.168.1.18:8000/v1/chat/completions"
M4_MODEL = "qwen3-0.6b"

# Tier 2: Thor Exo (local server - fast)
THOR_EXO_URL = "http://localhost:8000/v1/chat/completions"  
THOR_EXO_MODEL = "qwen3-0.6b"

# Tier 3: Thor Ollama (most reliable fallback)
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2:1b"

def generate_briefing(stats):
    """
    Generate a short 2-sentence morning briefing based on stats.
    3-tier failover: M4 Exo (1-2s) → Thor Exo (2-3s) → Thor Ollama (7s)
    """
    prompt = f"""Analyze these casino statistics and write a strictly 2-sentence executive summary highlighting the most interesting finding (e.g. highest jackpot, hottest area, or unusual activity).
Keep it professional but exciting. Do not use asterisks or markdown.

Stats:
- Total Jackpots: {stats.get('total_jackpots')}
- Avg Amount: ${stats.get('avg_jackpot')}
- Hottest Area: {stats.get('hot_areas', [{}])[0].get('location_id', 'N/A')}
- Recent Hits (1h): {stats.get('recent_count')}
- Best Machine: {stats.get('top_machines', [{}])[0].get('machine_name', 'N/A')}"""
    
    # Tier 1: Try M4 Exo first (fastest)
    try:
        payload = {
            "model": M4_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 60,
            "temperature": 0.7
        }
        response = requests.post(M4_EXO_URL, json=payload, timeout=3)
        if response.status_code == 200:
            return response.json().get('choices', [{}])[0].get('message', {}).get('content', '').strip()
    except Exception as e:
        logger.info(f"M4 Exo unavailable, trying Thor Exo: {e}")
    
    # Tier 2: Try Thor Exo (local, still fast)
    try:
        payload = {
            "model": THOR_EXO_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 60,
            "temperature": 0.7
        }
        response = requests.post(THOR_EXO_URL, json=payload, timeout=5)
        if response.status_code == 200:
            return response.json().get('choices', [{}])[0].get('message', {}).get('content', '').strip()
    except Exception as e:
        logger.info(f"Thor Exo unavailable, falling back to Ollama: {e}")
    
    # Tier 3: Fallback to Thor Ollama (most reliable)
    try:
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.7, "num_predict": 60}
        }
        response = requests.post(OLLAMA_URL, json=payload, timeout=30)
        if response.status_code == 200:
            return response.json().get('response', '').strip()
        else:
            logger.error(f"Ollama Error: {response.text}")
    except Exception as e:
        logger.error(f"All LLM services failed: {e}")
    
    return "Market activity is stable. Check the leaderboard for detailed insights."

def parse_search_query(query):
    """
    Convert natural language search query into structured filters.
    3-tier failover: M4 Exo → Thor Exo → return empty (graceful degradation)
    Returns JSON object.
    """
    prompt = f"""Extract search filters from this query: "{query}"
Output a valid JSON object with keys (all optional):
- location (string, e.g. "HD", "SL")
- min_amount (number)
- machine_name (string partial)
- sort (string: "recent", "amount", "name")
- limit (integer)

Example: "Show me high limit buffalo slots over $5000"
JSON: {{"location": "HD", "machine_name": "Buffalo", "min_amount": 5000, "sort": "amount"}}

Respond ONLY with the JSON object."""
    
    # Tier 1: Try M4 Exo
    try:
        payload = {
            "model": M4_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 150,
            "temperature": 0.1
        }
        response = requests.post(M4_EXO_URL, json=payload, timeout=3)
        if response.status_code == 200:
            content = response.json().get('choices', [{}])[0].get('message', {}).get('content', '{}')
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
    except Exception as e:
        logger.info(f"M4 Exo unavailable for search, trying Thor Exo: {e}")
    
    # Tier 2: Try Thor Exo
    try:
        payload = {
            "model": THOR_EXO_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 150,
            "temperature": 0.1
        }
        response = requests.post(THOR_EXO_URL, json=payload, timeout=5)
        if response.status_code == 200:
            content = response.json().get('choices', [{}])[0].get('message', {}).get('content', '{}')
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
    except Exception as e:
        logger.info(f"Thor Exo unavailable for search: {e}")
    
    # Graceful degradation: return empty filters (search will show all results)
    logger.warning(f"All LLM services unavailable for search query: {query}")
    return {}
