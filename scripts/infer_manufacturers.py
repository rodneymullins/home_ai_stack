#!/usr/bin/env python3
"""
Intelligent Manufacturer Inference
Uses machine name patterns and known game families to auto-detect manufacturers
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db_pool import get_connection
import re

# Manufacturer signature patterns
MANUFACTURER_PATTERNS = {
    'IGT': [
        r'WHEEL OF FORTUNE',
        r'TRIPLE RED HOT',
        r'DOUBLE DIAMOND',
        r'CLEOPATRA',
        r'SIBERIAN STORM',
        r'DA VINCI',
        r'TEXAS TEA',
        r'PROWLING PANTHER',
        r'GOLDEN GODDESS',
        r'KITTY GLITTER',
        r'PIXIES OF THE FOREST',
        r'ELVIS',
        r'FIRE OPALS',
        r'COYOTE MOON',
        r'SPHINX',
    ],
    'Aristocrat': [
        r'BUFFALO',
        r'LIGHTNING LINK',
        r'DRAGON LINK',
        r'5 DRAGONS',
        r'MORE CHILLI',
        r'POMPEII',
        r'WHERE\'?S THE GOLD',
        r'QUEEN OF THE NILE',
        r'50 LIONS',
        r'MISS KITTY',
        r'BIG RED',
        r'WILD PANDA',
        r'PELICAN PETE',
        r'MORE HEARTS',
    ],
    'Konami': [
        r'CHINA SHORES',
        r'LOTUS LAND',
        r'ROMAN TRIBUNE',
        r'LION FESTIVAL',
        r'CHILI CHILI FIRE',
        r'AFRICAN DIAMOND',
        r'WILD LEPRE\'?COINS',
        r'SOLSTICE CELEBRATION',
        r'GOLD STACKS',
        r'JEWEL REWARD',
    ],
    'Everi': [
        r'LOCK IT LINK',
        r'CASH MACHINE',
        r'JACKPOT VAULT',
        r'EMPIRE RICHES',
        r'MONEY FROG',
    ],
    'Ainsworth': [
        r'MUSTANG MONEY',
        r'EAGLE BUCKS',
        r'SUPER BUCKS',
        r'ROAMING REELS',
    ],
    'AGS': [
        r'RAKIN\' BACON',
        r'GOLDEN WINS',
    ],
}

def infer_manufacturer(machine_name):
    """Infer manufacturer from machine name patterns"""
    name_upper = machine_name.upper()
    
    for manufacturer, patterns in MANUFACTURER_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, name_upper):
                return manufacturer, pattern
    
    return None, None

def enrich_machines():
    """Auto-enrich machines using pattern matching"""
    print("\n🔍 INTELLIGENT MANUFACTURER INFERENCE")
    print("=" * 70)
    
    conn = get_connection()
    cur = conn.cursor()
    
    # Get active machines without manufacturer
    cur.execute("""
        SELECT DISTINCT j.machine_name
        FROM jackpots j
        LEFT JOIN slot_machines sm ON j.machine_name = sm.machine_name
        WHERE j.scraped_at > NOW() - INTERVAL '30 days'
        AND (sm.manufacturer IS NULL OR sm.manufacturer = '')
        ORDER BY j.machine_name
    """)
    
    machines = [row[0] for row in cur.fetchall()]
    
    print(f"Active machines without manufacturer: {len(machines)}")
    print()
    
    enriched_count = 0
    matched_machines = []
    
    for machine_name in machines:
        manufacturer, pattern = infer_manufacturer(machine_name)
        
        if manufacturer:
            # Update slot_machines table
            cur.execute("""
                UPDATE slot_machines
                SET manufacturer = %s
                WHERE machine_name = %s
            """, (manufacturer, machine_name))
            
            if cur.rowcount > 0:
                enriched_count += 1
                matched_machines.append((machine_name, manufacturer, pattern))
                print(f"✅ {machine_name[:50]:50} → {manufacturer:12} (matched: {pattern})")
    
    conn.commit()
    
    print()
    print("=" * 70)
    print(f"📊 RESULTS")
    print("=" * 70)
    print(f"Total processed: {len(machines)}")
    print(f"Successfully enriched: {enriched_count}")
    print(f"Remaining: {len(machines) - enriched_count}")
    print(f"Success rate: {enriched_count/len(machines)*100:.1f}%")
    
    # Get updated stats
    cur.execute("""
        SELECT COUNT(DISTINCT j.machine_name)
        FROM jackpots j
        INNER JOIN slot_machines sm ON j.machine_name = sm.machine_name
        WHERE j.scraped_at > NOW() - INTERVAL '30 days'
        AND sm.manufacturer IS NOT NULL
    """)
    active_with_mfg = cur.fetchone()[0]
    
    print()
    print(f"Active machines with manufacturer: {active_with_mfg}/554 ({active_with_mfg/554*100:.1f}%)")
    
    cur.close()
    conn.close()
    
    return enriched_count

if __name__ == "__main__":
    enrich_machines()
