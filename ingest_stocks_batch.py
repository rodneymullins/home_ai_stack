#!/usr/bin/env python3
"""
Batch stock data ingestion with single LLM call for categorization.
Much faster than per-memory categorization.
"""

import yfinance as yf
import requests
import json
import time
from datetime import datetime

# Popular stocks to track
STOCKS = [
    "AAPL",   # Apple
    "MSFT",   # Microsoft
    "GOOGL",  # Google
    "AMZN",   # Amazon
    "NVDA",   # NVIDIA
    "TSLA",   # Tesla
    "META",   # Meta
    "BRK-B"   # Berkshire Hathaway
]

def batch_categorize(memories_list):
    """
    Categorize all memories in a single LLM call.
    Returns list of metadata dicts matching input order.
    """
    # Build prompt with all memories indexed
    prompt = """Analyze these stock market facts and extract metadata for each. Return ONLY valid JSON array.

Facts:
"""
    for i, mem in enumerate(memories_list):
        prompt += f"{i}. {mem}\n"
    
    prompt += """
Return JSON array with this exact format:
[
  {"category": "knowledge", "keywords": ["keyword1", "keyword2"]},
  {"category": "knowledge", "keywords": ["keyword1", "keyword2"]},
  ...
]

Categories: knowledge, finance, technology, business, other
JSON array only:"""

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "functiongemma",
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1}
            },
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            response_text = result.get('response', '').strip()
            
            # Extract JSON array
            start = response_text.find('[')
            end = response_text.rfind(']') + 1
            
            if start != -1 and end > start:
                json_str = response_text[start:end]
                metadata_list = json.loads(json_str)
                
                # Ensure we got the right number
                if len(metadata_list) == len(memories_list):
                    return metadata_list
        
        print("⚠️  Batch categorization failed, using defaults")
    except Exception as e:
        print(f"❌ Error in batch categorization: {e}")
    
    # Fallback: return default metadata for all
    return [{"category": "knowledge", "keywords": []} for _ in memories_list]

def remember_batch(content, user_id="stock_bot", metadata=None):
    """Call the MCP remember tool via direct memory instance."""
    try:
        import sys
        sys.path.insert(0, '/home/rod/home_ai_stack')
        from src.core.mem0_config import create_memory
        
        memory = create_memory()
        messages = [{"role": "user", "content": content}]
        result = memory.add(messages, user_id=user_id, metadata=metadata or {})
        return result
    except Exception as e:
        print(f"❌ Error saving: {e}")
        return None

def fetch_stock_info(ticker):
    """Fetch stock information from Yahoo Finance."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Get recent price data
        hist = stock.history(period="1d")
        current_price = hist['Close'].iloc[-1] if not hist.empty else info.get('currentPrice', 'N/A')
        
        return {
            'ticker': ticker,
            'name': info.get('longName', ticker),
            'sector': info.get('sector', 'Unknown'),
            'industry': info.get('industry', 'Unknown'),
            'current_price': current_price,
            'market_cap': info.get('marketCap', 'N/A'),
            'pe_ratio': info.get('trailingPE', 'N/A'),
            'description': info.get('longBusinessSummary', 'N/A')[:300]
        }
    except Exception as e:
        print(f"❌ Error fetching {ticker}: {e}")
        return None

def main():
    print("🚀 Starting BATCH stock data ingestion...\n")
    
    # Step 1: Fetch all stock data
    all_stocks = []
    all_memories = []
    
    for ticker in STOCKS:
        print(f"📊 Fetching {ticker}...")
        stock_data = fetch_stock_info(ticker)
        
        if not stock_data:
            continue
            
        all_stocks.append(stock_data)
        
        # Create memories
        memories = [
            f"{stock_data['name']} ({ticker}) is in the {stock_data['sector']} sector, {stock_data['industry']} industry.",
            f"{ticker} trades at ${stock_data['current_price']:.2f}, market cap ${stock_data['market_cap']:,}, P/E {stock_data['pe_ratio']}.",
            f"{ticker}: {stock_data['description']}"
        ]
        all_memories.extend(memories)
    
    print(f"\n📦 Collected {len(all_memories)} memories from {len(all_stocks)} stocks")
    print(f"🧠 Batch categorizing with FunctionGemma (1 LLM call)...")
    
    # Step 2: Batch categorize ALL memories in one call
    start_time = time.time()
    metadata_list = batch_categorize(all_memories)
    categorization_time = time.time() - start_time
    
    print(f"✅ Categorized {len(all_memories)} memories in {categorization_time:.1f}s")
    
    # Step 3: Save with metadata
    print("\n💾 Saving to memory system...")
    for i, (mem, meta) in enumerate(zip(all_memories, metadata_list)):
        # Add stock-specific metadata
        ticker_idx = i // 3  # 3 memories per stock
        if ticker_idx < len(all_stocks):
            meta['ticker'] = all_stocks[ticker_idx]['ticker']
            meta['sector'] = all_stocks[ticker_idx]['sector']
            meta['date'] = datetime.now().isoformat()
        
        remember_batch(mem, metadata=meta)
        print(f"  ✓ Saved memory {i+1}/{len(all_memories)}")
    
    total_time = time.time() - start_time
    print(f"\n\n✅ COMPLETE! Ingested {len(all_memories)} memories in {total_time:.1f}s")
    print(f"   Categorization: {categorization_time:.1f}s (1 LLM call)")
    print(f"   Avg: {total_time/len(all_memories):.2f}s per memory")
    print("🔍 Check Neo4j Browser: http://192.168.1.211:7474")  # TODO: Move to config

if __name__ == "__main__":
    main()
