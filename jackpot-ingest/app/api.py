"""Flask REST API for iPhone/WiFi access"""
from flask import Flask, jsonify, request
from .db import get_conn

def create_app():
    app = Flask(__name__)

    @app.get("/health")
    def health():
        """Health check"""
        return jsonify({"ok": True, "service": "multi-casino-jackpots"})

    @app.get("/jackpots/latest")
    def latest():
        """Get latest jackpots across all casinos"""
        limit = min(int(request.args.get("limit", "50")), 200)
        
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                  SELECT 
                    m.scraped_at,
                    m.casino,
                    m.machine_name as game,
                    m.amount,
                    m.date_text as posted_date,
                    m.source_url
                  FROM multi_casino_jackpots m
                  ORDER BY m.scraped_at DESC
                  LIMIT %s
                """, (limit,))
                
                results = cur.fetchall()
                # Convert to JSON-serializable format
                output = []
                for r in results:
                    output.append({
                        'scraped_at': r['scraped_at'].isoformat() if r['scraped_at'] else None,
                        'casino': r['casino'],
                        'game': r['game'],
                        'amount': float(r['amount']) if r['amount'] else None,
                        'posted_date': r['posted_date'],
                        'source_url':r['source_url']
                    })
                
                return jsonify(output)
        finally:
            conn.close()
    
    @app.get("/jackpots/stats")
    def stats():
        """Get statistics by casino"""
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                  SELECT 
                    casino,
                    COUNT(*) as total_jackpots,
                    SUM(amount) as total_amount,
                    AVG(amount) as avg_amount,
                    MAX(amount) as max_amount
                  FROM multi_casino_jackpots
                  GROUP BY casino
                  ORDER BY total_amount DESC
                """)
                
                results = cur.fetchall()
                return jsonify([{
                    'casino': r['casino'],
                    'total_jackpots': r['total_jackpots'],
                    'total_amount': float(r['total_amount']) if r['total_amount'] else 0,
                    'avg_amount': float(r['avg_amount']) if r['avg_amount'] else 0,
                    'max_amount': float(r['max_amount']) if r['max_amount'] else 0,
                } for r in results])
        finally:
            conn.close()

    return app
