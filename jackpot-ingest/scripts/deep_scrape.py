#!/usr/bin/env python3
"""
DEEP SCRAPER - One-time historical data collection
Runs with pagination to collect ALL available jackpot history
"""
import sys
sys.path.insert(0, '/home/rod/jackpot-ingest')

from app.ingest import SCRAPERS
from app.db import get_conn, upsert_source
from app.normalize import fingerprint
from decimal import Decimal

# Override scrapers with pagination
import requests
from bs4 import BeautifulSoup
import re
from dateutil import parser as dtp

def deep_scrape_mohegan():
    """Scrape ALL Mohegan newsroom pages with pagination"""
    casino = "Mohegan Sun"
    property_ = "Mohegan Sun (CT)"
    base_url = "https://newsroom.mohegansun.com/category/jackpots/"
    
    all_urls = []
    page = 1
    
    # Paginate through all newsroom pages
    while page <= 20:  # Max 20 pages
        url = f"{base_url}page/{page}/" if page > 1 else base_url
        try:
            r = requests.get(url, timeout=10)
            if r.status_code != 200:
                break
            
            soup = BeautifulSoup(r.text, "lxml")
            articles = soup.select("article a[href]")
            urls_found = []
            
            for a in articles:
                href = a.get("href", "")
                if href.startswith("https://newsroom.mohegansun.com/") and re.search(r"/\d{4}/\d{2}/\d{2}/", href):
                    urls_found.append(href)
            
            if not urls_found:
                break
            
            all_urls.extend(urls_found)
            print(f"  Page {page}: {len(urls_found)} articles")
            page += 1
            
        except:
            break
    
    print(f"  Total Mohegan articles found: {len(all_urls)}")
    return list(dict.fromkeys(all_urls))

def main():
    """Deep scrape ALL historical data"""
    conn = get_conn()
    
    print("🔍 DEEP SCRAPE - Collecting ALL historical jackpot data\n")
    
    # Mohegan Sun with pagination
    print("📰 Mohegan Sun (with pagination)...")
    mohegan_urls = deep_scrape_mohegan()
    
    money_re = re.compile(r"\$([\d,]+(?:\.\d{2})?)")
    source_id = upsert_source(conn, "Mohegan Sun", "Mohegan Sun (CT)", "https://newsroom.mohegansun.com/category/jackpots/")
    
    inserted = 0
    for i, url in enumerate(mohegan_urls, 1):
        try:
            p = requests.get(url, timeout=10)
            ps = BeautifulSoup(p.text, "lxml")
            title = (ps.select_one("h1") or ps.title).get_text(" ", strip=True)
            body = ps.get_text("\n")
            
            time_el = ps.select_one("time")
            posted_date = None
            if time_el and time_el.get("datetime"):
                posted_date = dtp.parse(time_el["datetime"]).date()
            
            m = money_re.search(body)
            amount = float(m.group(1).replace(",", "")) if m else None
            
            if amount:
                fp = fingerprint(url, posted_date, Decimal(str(amount)) if amount else None, None, None)
                
                with conn.cursor() as cur:
                    cur.execute("""
                      INSERT INTO multi_casino_jackpots
                        (casino, machine_name, amount, date_text, source_url, source_id)
                      VALUES (%s, %s, %s, %s, %s, %s)
                      ON CONFLICT DO NOTHING
                    """, ("Mohegan Sun", "Unknown", amount, str(posted_date) if posted_date else None, url, source_id))
                    inserted += cur.rowcount
                
                if i % 50 == 0:
                    conn.commit()
                    print(f"  Processed {i}/{len(mohegan_urls)}, inserted {inserted} new")
            
        except:
            continue
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ Deep scrape complete: {inserted} total jackpots added")

if __name__ == "__main__":
    main()
