#!/usr/bin/env python3
"""
Data Transformer - Enrich and standardize casino jackpot data
Adds computed fields to existing jackpots table for advanced analytics
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import re

# Database configuration - matches google_trends_dashboard.py
DB_CONFIG = {'database': 'postgres', 'user': 'rod'}

def get_db_connection():
    """Get database connection"""
    try:
        return psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        print(f"DB connection error: {e}")
        return None

def classify_manufacturer(machine_name):
    """Detect manufacturer from machine name"""
    if not machine_name:
        return 'Unknown'
    
    name_upper = machine_name.upper()
    
    # Aristocrat games
    aristocrat_games = ['BUFFALO', 'LIGHTNING LINK', 'DRAGON LINK', 'TIMBERWOLF', 
                        'POMPEII', 'WILD PANDA', '50 LIONS', 'CHOY SUN DOA',
                        'QUEEN OF THE NILE', 'MISS KITTY', 'BIG RED']
    if any(game in name_upper for game in aristocrat_games):
        return 'Aristocrat'
    
    # IGT games
    igt_games = ['WHEEL OF FORTUNE', 'CLEOPATRA', 'TRIPLE DIAMOND', 'DOUBLE DIAMOND',
                 'TRIPLE RED HOT', 'GOLDEN GODDESS', 'DAVINCI DIAMONDS', 'KITTY GLITTER',
                 'SIBERIAN STORM', 'TEXAS TEA', 'LOBSTERMANIA', 'WOLF RUN']
    if any(game in name_upper for game in igt_games):
        return 'IGT'
    
    # Light & Wonder (Scientific Games)
    lnw_games = ['LOCK IT LINK', 'HUFF N PUFF', 'JINSE DAO', 'FU DAO LE',
                 'DANCING DRUMS', 'ULTIMATE FIRE LINK', '88 FORTUNES', 'MIGHTY CASH']
    if any(game in name_upper for game in lnw_games):
        return 'Light & Wonder'
    
    # Konami
    konami_games = ['CHINA SHORES', 'LOTUS LAND', 'SOLSTICE CELEBRATION',
                    'CHILI CHILI FIRE', 'RICHES', 'FORTUNE STACKS']
    if any(game in name_upper for game in konami_games):
        return 'Konami'
    
    # Everi
    everi_games = ['CASH ERUPTION', 'SMOKIN HOT STUFF', 'JACKPOT VAULT']
    if any(game in name_upper for game in everi_games):
        return 'Everi'
    
    return 'Other'

def extract_game_family(machine_name):
    """Extract game family/series from machine name"""
    if not machine_name:
        return 'Unknown'
    
    name_upper = machine_name.upper()
    
    # Common game families
    families = {
        'Buffalo': ['BUFFALO'],
        'Lightning Link': ['LIGHTNING LINK'],
        'Dragon Link': ['DRAGON LINK'],
        'Wheel of Fortune': ['WHEEL OF FORTUNE'],
        'Lock It Link': ['LOCK IT LINK'],
        'Ultimate Fire Link': ['ULTIMATE FIRE LINK'],
        '88 Fortunes': ['88 FORTUNES'],
        'Dancing Drums': ['DANCING DRUMS'],
        'Fu Dao Le': ['FU DAO LE'],
        'Cleopatra': ['CLEOPATRA'],
        'Triple Diamond': ['TRIPLE DIAMOND'],
        'Double Diamond': ['DOUBLE DIAMOND'],
        'Golden Goddess': ['GOLDEN GODDESS'],
        'China Shores': ['CHINA SHORES'],
        'Mighty Cash': ['MIGHTY CASH'],
        'Huff N Puff': ['HUFF N PUFF']
    }
    
    for family, keywords in families.items():
        if any(kw in name_upper for kw in keywords):
            return family
    
    # Extract first 2-3 words as family if no match
    words = machine_name.split()
    if len(words) >= 2:
        return ' '.join(words[:2])
    
    return machine_name

def normalize_machine_name(machine_name):
    """Standardize machine name format"""
    if not machine_name:
        return 'Unknown'
    
    # Remove extra whitespace
    normalized = ' '.join(machine_name.split())
    
    # Convert to title case
    normalized = normalized.title()
    
    # Common replacements
    replacements = {
        'Deluxe': 'DLX',
        'Premium': 'PREM',
        'Extreme': 'XTREME'
    }
    
    for old, new in replacements.items():
        normalized = normalized.replace(old, new)
    
    return normalized

def normalize_denomination(denom):
    """Standardize denomination format"""
    if not denom:
        return 'Unknown'
    
    # Remove whitespace
    denom = denom.strip()
    
    # Already in good format
    if re.match(r'^\$\d+\.\d{2}$', denom):
        return denom
    
    # Extract numeric value
    match = re.search(r'(\d+\.?\d*)', denom)
    if match:
        value = float(match.group(1))
        # Handle cents
        if value < 1:
            return f"${value:.2f}"
        # Handle dollars
        return f"${value:.2f}"
    
    return denom

def classify_payout_tier(amount):
    """Categorize jackpot by payout size"""
    if amount is None:
        return 'Unknown'
    
    if amount < 500:
        return 'Small'
    elif amount < 2000:
        return 'Medium'
    elif amount < 10000:
        return 'Large'
    else:
        return 'Mega'

def add_transformation_columns():
    """Add new columns to jackpots table"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        
        # Add columns if they don't exist
        columns = [
            "ALTER TABLE jackpots ADD COLUMN IF NOT EXISTS manufacturer TEXT",
            "ALTER TABLE jackpots ADD COLUMN IF NOT EXISTS game_family TEXT",
            "ALTER TABLE jackpots ADD COLUMN IF NOT EXISTS payout_tier TEXT",
            "ALTER TABLE jackpots ADD COLUMN IF NOT EXISTS hour_of_day INTEGER",
            "ALTER TABLE jackpots ADD COLUMN IF NOT EXISTS day_of_week INTEGER",
            "ALTER TABLE jackpots ADD COLUMN IF NOT EXISTS is_weekend BOOLEAN",
            "ALTER TABLE jackpots ADD COLUMN IF NOT EXISTS normalized_machine_name TEXT",
            "ALTER TABLE jackpots ADD COLUMN IF NOT EXISTS normalized_denomination TEXT"
        ]
        
        for sql in columns:
            cur.execute(sql)
        
        # Create indexes
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_manufacturer ON jackpots(manufacturer)",
            "CREATE INDEX IF NOT EXISTS idx_game_family ON jackpots(game_family)",
            "CREATE INDEX IF NOT EXISTS idx_hour_of_day ON jackpots(hour_of_day)",
            "CREATE INDEX IF NOT EXISTS idx_payout_tier ON jackpots(payout_tier)",
            "CREATE INDEX IF NOT EXISTS idx_is_weekend ON jackpots(is_weekend)"
        ]
        
        for sql in indexes:
            cur.execute(sql)
        
        conn.commit()
        cur.close()
        conn.close()
        
        print("✅ Database schema updated successfully")
        return True
        
    except Exception as e:
        print(f"❌ Schema update failed: {e}")
        return False

def transform_data(batch_size=1000):
    """Transform existing jackpot data"""
    conn = get_db_connection()
    if not conn:
        return
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get total count
        cur.execute("SELECT COUNT(*) as total FROM jackpots WHERE manufacturer IS NULL")
        total = cur.fetchone()['total']
        
        print(f"📊 Found {total} records to transform")
        
        processed = 0
        
        # Process in batches
        while processed < total:
            # Fetch batch
            cur.execute("""
                SELECT id, machine_name, denomination, amount, hit_timestamp
                FROM jackpots
                WHERE manufacturer IS NULL
                LIMIT %s
            """, (batch_size,))
            
            batch = cur.fetchall()
            if not batch:
                break
            
            # Transform each record
            for record in batch:
                manufacturer = classify_manufacturer(record['machine_name'])
                game_family = extract_game_family(record['machine_name'])
                normalized_name = normalize_machine_name(record['machine_name'])
                normalized_denom = normalize_denomination(record['denomination'])
                payout_tier = classify_payout_tier(record['amount'])
                
                # Extract time features
                hour_of_day = None
                day_of_week = None
                is_weekend = None
                
                if record['hit_timestamp']:
                    hour_of_day = record['hit_timestamp'].hour
                    day_of_week = record['hit_timestamp'].weekday()  # 0=Monday, 6=Sunday
                    is_weekend = day_of_week >= 5  # Saturday or Sunday
                
                # Update record
                cur.execute("""
                    UPDATE jackpots
                    SET manufacturer = %s,
                        game_family = %s,
                        normalized_machine_name = %s,
                        normalized_denomination = %s,
                        payout_tier = %s,
                        hour_of_day = %s,
                        day_of_week = %s,
                        is_weekend = %s
                    WHERE id = %s
                """, (manufacturer, game_family, normalized_name, normalized_denom,
                      payout_tier, hour_of_day, day_of_week, is_weekend, record['id']))
            
            conn.commit()
            processed += len(batch)
            
            print(f"⚙️  Processed {processed}/{total} records ({processed*100//total}%)")
        
        cur.close()
        conn.close()
        
        print(f"✅ Transformation complete! Processed {processed} records")
        
    except Exception as e:
        print(f"❌ Transformation failed: {e}")

def show_statistics():
    """Display transformation statistics"""
    conn = get_db_connection()
    if not conn:
        return
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        print("\n📊 TRANSFORMATION STATISTICS\n")
        
        # Manufacturer breakdown
        cur.execute("""
            SELECT manufacturer, COUNT(*) as count, 
                   ROUND(AVG(amount), 2) as avg_payout
            FROM jackpots
            WHERE manufacturer IS NOT NULL
            GROUP BY manufacturer
            ORDER BY count DESC
        """)
        
        print("Manufacturers:")
        for row in cur.fetchall():
            print(f"  {row['manufacturer']}: {row['count']} hits, avg ${row['avg_payout']}")
        
        # Payout tier breakdown
        cur.execute("""
            SELECT payout_tier, COUNT(*) as count
            FROM jackpots
            WHERE payout_tier IS NOT NULL
            GROUP BY payout_tier
            ORDER BY 
                CASE payout_tier
                    WHEN 'Small' THEN 1
                    WHEN 'Medium' THEN 2
                    WHEN 'Large' THEN 3
                    WHEN 'Mega' THEN 4
                END
        """)
        
        print("\nPayout Tiers:")
        for row in cur.fetchall():
            print(f"  {row['payout_tier']}: {row['count']} hits")
        
        # Top game families
        cur.execute("""
            SELECT game_family, COUNT(*) as count
            FROM jackpots
            WHERE game_family IS NOT NULL
            GROUP BY game_family
            ORDER BY count DESC
            LIMIT 10
        """)
        
        print("\nTop Game Families:")
        for row in cur.fetchall():
            print(f"  {row['game_family']}: {row['count']} hits")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Statistics failed: {e}")

if __name__ == '__main__':
    print("🎰 CASINO DATA TRANSFORMER\n")
    
    # Step 1: Update schema
    print("Step 1: Updating database schema...")
    if not add_transformation_columns():
        print("❌ Failed to update schema. Exiting.")
        exit(1)
    
    # Step 2: Transform data
    print("\nStep 2: Transforming data...")
    transform_data()
    
    # Step 3: Show statistics
    show_statistics()
    
    print("\n✅ All done!")
