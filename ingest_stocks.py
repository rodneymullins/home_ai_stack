#!/usr/bin/env python3
"""
Stock data ingestion script for testing Mem0 auto-categorization.
Downloads stock information from Yahoo Finance and stores in memory.
"""

import yfinance as yf
from config import DB_CONFIG
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

def remember_via_mcp(content, user_id="stock_bot", metadata=None):
    """Call the MCP remember tool via direct memory instance."""
    try:
        # Import the memory instance
        import sys
        sys.path.insert(0, '/home/rod/home_ai_stack')
        from src.core.mem0_config import create_memory
        
        memory = create_memory()
        messages = [{"role": "user", "content": content}]
        result = memory.add(messages, user_id=user_id, metadata=metadata or {})
        print(f"✅ Saved: {content[:80]}...")
        return result
    except Exception as e:
        print(f"❌ Error saving: {e}")
        return None

def fetch_stock_info(ticker):
    """Fetch stock information from Yahoo Finance."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cur = conn.cursor()
        except Exception as db_e:
            print(f"❌ Error connecting to database: {db_e}")
            # Decide how to handle this error: continue without DB, or re-raise
            # For now, we'll just print and proceed without DB operations if connection fails
            conn = None
            cur = None
        
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
            'dividend_yield': info.get('dividendYield', 0),
            'description': info.get('longBusinessSummary', 'N/A')
        }
    except Exception as e:
        print(f"❌ Error fetching {ticker}: {e}")
        return None

def main():
    print("🚀 Starting stock data ingestion...\n")
    
    for ticker in STOCKS:
        print(f"\n📊 Fetching {ticker}...")
        stock_data = fetch_stock_info(ticker)
        
        if not stock_data:
            continue
        
        # Create memory-friendly summaries
        memories = [
            # Basic info
            f"{stock_data['name']} ({ticker}) is a company in the {stock_data['sector']} sector, specifically in {stock_data['industry']}.",
            
            # Price and valuation
            f"{ticker} is currently trading at ${stock_data['current_price']:.2f} with a market cap of ${stock_data['market_cap']:,} and P/E ratio of {stock_data['pe_ratio']}.",
            
            # Business description (truncated)
            f"{ticker} business overview: {stock_data['description'][:300]}..." if stock_data['description'] != 'N/A' else None
        ]
        
        # Store each memory with metadata
        for mem in memories:
            if mem:
                # Auto-categorization will kick in, but we can also provide metadata
                metadata = {
                    "ticker": ticker,
                    "sector": stock_data['sector'],
                    "date": datetime.now().isoformat()
                }
                remember_via_mcp(mem, metadata=metadata)
                time.sleep(0.5)  # Rate limiting
    
    print("\n\n✅ Stock data ingestion complete!")
    print(f"🔍 Check Neo4j Browser to see the knowledge graph: http://{DB_CONFIG['host']}:7474")

if __name__ == "__main__":
    main()
