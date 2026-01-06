#!/usr/bin/env python3
"""
LLM-Powered Manufacturer Inference
Uses M4 Exo to intelligently infer manufacturers from machine names
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db_pool import get_connection
import requests
import json
import time

# M4 Exo endpoint
EXO_URL = "http://192.168.1.18:8000/v1/chat/completions"
MODEL = "qwen3-0.6b"

KNOWN_MANUFACTURERS = [
    "IGT",
    "Aristocrat",
    "Konami",
    "Everi",
    "Ainsworth",
    "AGS",
    "Scientific Games",
    "Bally",
    "WMS",
    "Spielo"
]

def ask_llm_for_manufacturer(machine_name):
    """Use LLM to infer manufacturer from machine name"""
    prompt = f"""You are a slot machine expert. Given a slot machine name, identify the manufacturer.

Machine Name: "{machine_name}"

Known manufacturers: {', '.join(KNOWN_MANUFACTURERS)}

Respond with ONLY the manufacturer name from the list above, or "Unknown" if uncertain.
Do not include any explanation, just the manufacturer name."""

    try:
        payload = {
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 20,
            "temperature": 0.1
        }
        
        response = requests.post(EXO_URL, json=payload, timeout=5)
        
        if response.status_code == 200:
            content = response.json().get('choices', [{}])[0].get('message', {}).get('content', '').strip()
            
            # Clean up response
            content = content.replace('"', '').replace("'", '').strip()
            
            # Validate it's a known manufacturer
            if content in KNOWN_MANUFACTURERS:
                return content
            
            # Try case-insensitive match
            for mfg in KNOWN_MANUFACTURERS:
                if content.lower() == mfg.lower():
                    return mfg
                    
        return None
        
    except Exception as e:
        print(f"   ⚠️ LLM error: {e}")
        return None

def enrich_with_llm(batch_size=50):
    """Use LLM to enrich remaining machines"""
    print("\n🤖 LLM-POWERED MANUFACTURER INFERENCE")
    print("=" * 70)
    print(f"Using M4 Exo ({MODEL}) for intelligent fuzzy matching")
    print()
    
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
        LIMIT %s
    """, (batch_size,))
    
    machines = [row[0] for row in cur.fetchall()]
    
    print(f"Processing {len(machines)} machines (batch size: {batch_size})")
    print()
    
    enriched_count = 0
    failed_count = 0
    
    for i, machine_name in enumerate(machines, 1):
        print(f"[{i}/{len(machines)}] {machine_name[:50]:50} ... ", end="", flush=True)
        
        manufacturer = ask_llm_for_manufacturer(machine_name)
        
        if manufacturer and manufacturer != "Unknown":
            # Update database
            cur.execute("""
                UPDATE slot_machines
                SET manufacturer = %s
                WHERE machine_name = %s
            """, (manufacturer, machine_name))
            
            if cur.rowcount > 0:
                enriched_count += 1
                print(f"✅ {manufacturer}")
                conn.commit()
            else:
                print(f"⚠️ Update failed")
                failed_count += 1
        else:
            print(f"❓ Unknown")
            failed_count += 1
        
        # Small delay to avoid overwhelming the LLM
        time.sleep(0.1)
    
    print()
    print("=" * 70)
    print(f"📊 RESULTS")
    print("=" * 70)
    print(f"Processed: {len(machines)}")
    print(f"Successfully enriched: {enriched_count}")
    print(f"Failed/Unknown: {failed_count}")
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
    print(f"🎯 Active machines with manufacturer: {active_with_mfg}/554 ({active_with_mfg/554*100:.1f}%)")
    
    cur.close()
    conn.close()
    
    return enriched_count

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='LLM-powered manufacturer inference')
    parser.add_argument('--batch-size', type=int, default=50, help='Number of machines to process')
    args = parser.parse_args()
    
    enrich_with_llm(batch_size=args.batch_size)
