#!/usr/bin/env python3
"""
Comprehensive jackpot data aggregator
Combines all public jackpot sources for maximum historical depth
"""
import sys
sys.path.insert(0, '/home/rod/jackpot-ingest')

from app.db import get_conn, upsert_source
from decimal import Decimal
import importlib

# Import all scraper modules
from app.scrapers.foxwoods import FoxwoodsSlots
from app.scrapers.mohegan import MoheganJackpots
from app.scrapers.hardrock_tampa import HardRockTampa
from app.scrapers.choctaw import ChoctawDurant
from app.scrapers.misc import Pechanga

# Additional high-value sources
try:
    from app.scrapers.igt_library import scrape_igt_jackpots_library
    from app.scrapers.casino_org import scrape_casino_org_jackpots
except:
    scrape_igt_jackpots_library = None
    scrape_casino_org_jackpots = None

def main():
    """Aggregate ALL public jackpot data"""
    conn = get_conn()
    
    print("🎰 COMPREHENSIVE JACKPOT DATA AGGREGATION\n")
    print("=" * 70)
    
    total_inserted = 0
    
    # Original casino scrapers
    casino_scrapers = [
        FoxwoodsSlots(),
        MoheganJackpots(),
        HardRockTampa(),
        ChoctawDurant(),
        Pechanga(),
    ]
    
    for scraper in casino_scrapers:
        print(f"\n📍 {scraper.casino} - {scraper.property}")
        source_id = upsert_source(conn, scraper.casino, scraper.property, scraper.base_url)
        
        jackpots = scraper.fetch()
        inserted = 0
        
        for jp in jackpots:
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                      INSERT INTO multi_casino_jackpots
                        (casino, machine_name, amount, date_text, source_url, source_id)
                      VALUES (%s, %s, %s, %s, %s, %s)
                      ON CONFLICT DO NOTHING
                    """, (
                        scraper.casino,
                        jp.get('game') or jp.get('machine_name') or 'Unknown',
                        jp.get('amount'),
                        str(jp.get('posted_date')) if jp.get('posted_date') else None,
                        jp.get('source_url') or scraper.base_url,
                        source_id
                    ))
                    inserted += cur.rowcount
            except:
                continue
        
        conn.commit()
        total_inserted += inserted
        print(f"  ✓ {inserted} jackpots added")
    
    # IGT Jackpots Library
    if scrape_igt_jackpots_library:
        print(f"\n🎯 IGT Jackpots Library (Progressive Network)")
        source_id = upsert_source(conn, 'IGT Network', 'Progressive Jackpots', 'https://www.igtjackpots.com')
        
        jackpots = scrape_igt_jackpots_library()
        inserted = 0
        
        for jp in jackpots:
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                      INSERT INTO multi_casino_jackpots
                        (casino, machine_name, amount, date_text, source_url, source_id)
                      VALUES (%s, %s, %s, %s, %s, %s)
                      ON CONFLICT DO NOTHING
                    """, (
                        jp['casino'],
                        jp['machine_name'],
                        jp['amount'],
                        jp.get('date_text'),
                        jp['source_url'],
                        source_id
                    ))
                    inserted += cur.rowcount
            except:
                continue
        
        conn.commit()
        total_inserted += inserted
        print(f"  ✓ {inserted} jackpots added")
    
    # Casino.org Progressive Tracker
    if scrape_casino_org_jackpots:
        print(f"\n🌐 Casino.org Progressive Tracker")
        source_id = upsert_source(conn, 'Online Progressive', 'Casino.org Tracker', 'https://www.casino.org/progressive-jackpots/')
        
        jackpots = scrape_casino_org_jackpots()
        inserted = 0
        
        for jp in jackpots:
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                      INSERT INTO multi_casino_jackpots
                        (casino, machine_name, amount, date_text, source_url, source_id)
                      VALUES (%s, %s, %s, %s, %s, %s)
                      ON CONFLICT DO NOTHING
                    """, (
                        jp['casino'],
                        jp['machine_name'],
                        jp['amount'],
                        jp.get('date_text'),
                        jp['source_url'],
                        source_id
                    ))
                    inserted += cur.rowcount
            except:
                continue
        
        conn.commit()
        total_inserted += inserted
        print(f"  ✓ {inserted} jackpots added")
    
    conn.close()
    
    print(f"\n{'=' * 70}")
    print(f"✅ TOTAL NEW JACKPOTS ADDED: {total_inserted}")
    print(f"{'=' * 70}\n")

if __name__ == "__main__":
    main()
