#!/usr/bin/env python3
"""
Quick bulk stock ingestion WITHOUT LLM categorization.
Saves with basic metadata for immediate use.
"""

import yfinance as yf
import sys
sys.path.insert(0, '/home/rod/home_ai_stack')
from src.core.mem0_config import create_memory

# Test with just 2 stocks first
STOCKS = ["AAPL", "MSFT"]

def main():
    print("🚀 Quick bulk ingestion (no LLM)...\n")
    memory = create_memory()
    
    for ticker in STOCKS:
        print(f"📊 {ticker}...")
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period="1d")
        price = hist['Close'].iloc[-1] if not hist.empty else 0
        
        # Save with basic metadata (no LLM call)
        metadata = {
            "category": "finance",
            "ticker": ticker,
            "sector": info.get('sector', 'Unknown'),
            "source": "yfinance"
        }
        
        memories = [
            f"{info.get('longName', ticker)} ({ticker}) is in {info.get('sector', 'tech')} sector.",
            f"{ticker} trades at ${price:.2f}, market cap ${info.get('marketCap', 0):,}.",
        ]
        
        for mem in memories:
            messages = [{"role": "user", "content": mem}]
            memory.add(messages, user_id="stock_bot", metadata=metadata)
            print(f"  ✓ {mem[:60]}...")
    
    print(f"\n✅ Done! Ingested {len(STOCKS) * 2} memories instantly")
    print("Run post_process_metadata.py to enrich with LLM categorization")

if __name__ == "__main__":
    main()
