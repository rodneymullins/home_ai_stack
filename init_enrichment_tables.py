#!/usr/bin/env python3
"""
Create database tables for external data enrichment
"""
import psycopg2
from config import DB_CONFIG

def create_enrichment_tables():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        print("Creating machine_specs table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS machine_specs (
                machine_name VARCHAR(255) PRIMARY KEY,
                rtp_percentage DECIMAL(5,2),
                max_bet VARCHAR(50),
                features TEXT[],
                theme TEXT,
                release_year INT,
                source VARCHAR(50),
                spec_url TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        print("Creating community_feedback table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS community_feedback (
                id SERIAL PRIMARY KEY,
                machine_name VARCHAR(255),
                source VARCHAR(50),
                sentiment VARCHAR(20),
                excerpt TEXT,
                author VARCHAR(255),
                posted_date TIMESTAMP,
                url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Indexes for performance
        print("Creating indexes...")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_specs_machine ON machine_specs(machine_name)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_feedback_machine ON community_feedback(machine_name)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_feedback_sentiment ON community_feedback(sentiment)")
        
        conn.commit()
        print("✅ Enrichment tables created successfully!")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    create_enrichment_tables()
