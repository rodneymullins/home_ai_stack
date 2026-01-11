import psycopg2
from config import DB_CONFIG
import sys

# Override DB name for this check
WEALTH_CONFIG = DB_CONFIG.copy()
WEALTH_CONFIG['database'] = 'wealth'

def check_wealth_db():
    print(f"🔌 Connecting to 'wealth' DB at {WEALTH_CONFIG['host']}...")
    try:
        conn = psycopg2.connect(**WEALTH_CONFIG)
        cur = conn.cursor()
        
        # Check tables
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables = [r[0] for r in cur.fetchall()]
        
        print(f"✅ Connection Successful!")
        print(f"📊 Tables found: {tables}")
        
        required = ['accounts', 'transactions', 'net_worth_log', 'recurring_transactions', 'assets_liabilities']
        missing = [t for t in required if t not in tables]
        
        if missing:
            print(f"⚠️  Missing Tables: {missing}")
            print("❌ Schema NOT fully applied.")
        else:
            print("✅ Schema looks GOOD.")
            
        cur.close()
        conn.close()
        
    except psycopg2.OperationalError as e:
        if 'does not exist' in str(e):
            print(f"❌ Database 'wealth' does not exist on {WEALTH_CONFIG['host']}")
        else:
            print(f"❌ Connection Failed: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_wealth_db()
