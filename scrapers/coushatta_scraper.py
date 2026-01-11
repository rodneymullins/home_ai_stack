#!/usr/bin/env python3
"""
Standalone Coushatta Casino Jackpot Scraper
Scrapes jackpot data from all pages and stores in PostgreSQL (with robust deduplication using fingerprint)
"""
import hashlib
import time
import re
from datetime import datetime
import sys
import os

import requests
from requests.adapters import HTTPAdapter, Retry
from bs4 import BeautifulSoup

from psycopg2.extras import RealDictCursor, execute_values

# Add parent directory to path to find utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from utils.db_pool import get_db_connection
except ImportError:
    # Fallback if utils not found (e.g. running standalone without project structure)
    import psycopg2
    from config import DB_CONFIG
    print("⚠️  Warning: utils.db_pool not found. Using config.py connection.")
    def get_db_connection():
        return psycopg2.connect(**DB_CONFIG)

BASE_URL = "https://www.coushattacasinoresort.com/gaming/slot-jackpot-updates/page/{}"
PAGES = 62
SLEEP_SECONDS = 0.5

TS_RE = re.compile(r"(\d{1,2}/\d{1,2}/\d{4} \d{1,2}:\d{2}:\d{2})")

def init_jackpot_table():
    conn = get_db_connection()
    if not conn:
        print("❌ Could not connect to DB")
        return
    try:
        with conn, conn.cursor() as cur:
            # Ensure the fingerprint index exists (DB migration should be complete)
            cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_jackpots_fingerprint ON jackpots(fingerprint);")
        print("✅ Jackpots table verification complete")
    finally:
        conn.close()

def build_session():
    s = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=0.7,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    s.mount("https://", HTTPAdapter(max_retries=retries))
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })
    return s

def parse_amount(text):
    if not text:
        return None
    amt = text.replace("$", "").replace(",", "").strip()
    try:
        return round(float(amt), 2)
    except ValueError:
        return None

def fingerprint_row(location_id, machine_name, hit_timestamp, amount, game_id, denomination):
    # Logic matches backfill script exactly
    ts_str = str(hit_timestamp) if hit_timestamp else ''
    
    # Amount handling to match backfill (float->round->str)
    amt_str = ''
    if amount is not None:
        try:
            amt_str = str(round(float(amount), 2))
        except:
            amt_str = str(amount)

    raw = f"{location_id}|{machine_name}|{ts_str}|{amt_str}|{game_id or ''}|{denomination or ''}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()

def scrape_jackpot_page(session, page_num):
    url = BASE_URL.format(page_num)
    r = session.get(url, timeout=20)
    if r.status_code != 200:
        print(f"❌ Page {page_num}: HTTP {r.status_code}")
        return []

    soup = BeautifulSoup(r.content, "html.parser")
    rows = soup.find_all("tr", class_="dataRow")
    jackpots = []

    for row in rows:
        caption = row.find("span", class_="caption")
        if not caption:
            continue

        caption_text = " ".join(caption.get_text(" ", strip=True).split())

        # Machine name
        machine_name = "Unknown"
        if "Title:" in caption_text and "Amount:" in caption_text:
            machine_name = caption_text.split("Title:", 1)[1].split("Amount:", 1)[0].strip()

        # Skip Poker & Keno
        up = machine_name.upper()
        if "POKER" in up or "KENO" in up:
            continue

        # Amount
        amount = None
        if "Amount:" in caption_text:
            chunk = caption_text.split("Amount:", 1)[1]
            if "Denomination:" in chunk:
                chunk = chunk.split("Denomination:", 1)[0]
            amount = parse_amount(chunk)

        # Denomination
        denomination = None
        if "Denomination:" in caption_text:
            chunk = caption_text.split("Denomination:", 1)[1]
            if "Game ID:" in chunk:
                chunk = chunk.split("Game ID:", 1)[0]
            denomination = chunk.strip() or None

        # Game ID
        game_id = None
        if "Game ID:" in caption_text:
            chunk = caption_text.split("Game ID:", 1)[1]
            if "Location:" in chunk:
                chunk = chunk.split("Location:", 1)[0]
            game_id = chunk.strip() or None

        # Location
        location_id = "Unknown"
        if "Location:" in caption_text:
            location_id = caption_text.split("Location:", 1)[1].strip() or "Unknown"

        # Timestamp
        hit_timestamp = None
        slot_title = row.find("span", class_="slotTitle")
        if slot_title:
            m = TS_RE.search(slot_title.get_text(" ", strip=True))
            if m:
                try:
                    hit_timestamp = datetime.strptime(m.group(1), "%m/%d/%Y %H:%M:%S")
                except ValueError:
                    hit_timestamp = None

        fp = fingerprint_row(location_id, machine_name, hit_timestamp, amount, game_id, denomination)

        jackpots.append({
            "fingerprint": fp,
            "location_id": location_id,
            "machine_name": machine_name,
            "denomination": denomination,
            "amount": amount,
            "game_id": game_id,
            "hit_timestamp": hit_timestamp,
            "page_num": page_num
        })

    return jackpots

def scrape_all_pages():
    print("🎰 Starting Coushatta jackpot scraper...")
    print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    session = build_session()
    conn = get_db_connection()
    if not conn:
        print("❌ DB Connection failed")
        return

    total_processed = 0
    new_inserted = 0

    try:
        with conn, conn.cursor() as cur:
            for page in range(1, PAGES + 1):
                jackpots = scrape_jackpot_page(session, page)
                total_processed += len(jackpots)

                if jackpots:
                    values = [
                        (
                            j["fingerprint"],
                            j["location_id"],
                            j["machine_name"],
                            j["denomination"],
                            j["amount"],
                            j["game_id"],
                            j["hit_timestamp"],
                            j["page_num"],
                        )
                        for j in jackpots
                    ]

                    # Uses fingerprint (single column) for fast deduplication
                    sql = """
                        INSERT INTO jackpots
                        (fingerprint, location_id, machine_name, denomination, amount, game_id, hit_timestamp, page_num)
                        VALUES %s
                        ON CONFLICT (fingerprint) DO NOTHING
                    """
                    execute_values(cur, sql, values, page_size=500)
                    if cur.rowcount and cur.rowcount > 0:
                        new_inserted += cur.rowcount

                if page % 10 == 0:
                    print(f"   Progress: {page}/{PAGES} pages scraped")

                time.sleep(SLEEP_SECONDS)
        
        conn.commit()

    finally:
        conn.close()

    print("✅ Scrape complete!")
    print(f"   Total processed: {total_processed}")
    print(f"   New entries (approx): {new_inserted}")
    print(f"   Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    init_jackpot_table()
    scrape_all_pages()
