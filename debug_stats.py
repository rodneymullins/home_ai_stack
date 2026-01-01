
import sys
import os

# Add the directory to the path so we can import
sys.path.append('/home/rod/home_ai_stack')

# We need to mock Flask app context if necessary, or just import the function
# The function uses get_db_connection which relies on global DB_CONFIG
from google_trends_dashboard import get_jackpot_stats, get_db_connection, DB_CONFIG

print("DB Config:", DB_CONFIG)

conn = get_db_connection()
print(f"Connection successful: {conn is not None}")
if conn:
    print("Connection status:", conn.status)
    conn.close()

print("\n--- calling get_jackpot_stats ---")
try:
    stats = get_jackpot_stats()
    print("Stats result:", stats)
except Exception as e:
    print(f"EXCEPTION: {e}")
    import traceback
    traceback.print_exc()
