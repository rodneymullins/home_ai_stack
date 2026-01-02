#!/usr/bin/env python3
"""
NBER (National Bureau of Economic Research) Paper Scraper
Fetches top economics working papers from NBER RSS feeds

NBER is the most prestigious economics research institution.
Papers here are extremely high quality (Nobel laureates, Fed economists, etc.)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import feedparser
import requests
from bs4 import BeautifulSoup
import psycopg2
from datetime import datetime
from pathlib import Path

from scrapers.domain_categorizer import categorize_paper
from scrapers.paper_quality import calculate_quality_score, should_store_paper

# Database config
DB_CONFIG = {'database': 'research_papers', 'user': 'rod', 'host': '192.168.1.211'}

# PDF storage
PDF_STORAGE_PATH = Path('/mnt/raid0/research_papers/pdfs/nber')
PDF_STORAGE_PATH.mkdir(parents=True, exist_ok=True)

# NBER RSS feeds by subject
NBER_RSS_FEEDS = {
    'all': 'https://www.nber.org/rss/new.xml',
    'macro': 'https://www.nber.org/rss/EFG.xml',  # Economic Fluctuations and Growth
    'finance': 'https://www.nber.org/rss/AP.xml',  # Asset Pricing
    'labor': 'https://www.nber.org/rss/LS.xml',  # Labor Studies
    'public': 'https://www.nber.org/rss/PE.xml',  # Public Economics
}

def get_db_connection():
    """Get database connection"""
    try:
        return psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        print(f"Database error: {e}")
        return None

def paper_exists(conn, nber_id):
    """Check if paper already exists"""
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM papers WHERE nber_id = %s", (nber_id,))
    exists = cur.fetchone() is not None
    cur.close()
    return exists

def extract_nber_id(url):
    """Extract NBER paper ID from URL"""
    # URL format: https://www.nber.org/papers/w12345
    if '/papers/w' in url:
        return url.split('/papers/')[1].split('?')[0]
    return None

def fetch_paper_details(nber_url):
    """Fetch detailed paper information from NBER page"""
    try:
        response = requests.get(nber_url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract abstract
        abstract_div = soup.find('div', class_='page-header__intro-inner')
        abstract = abstract_div.get_text(strip=True) if abstract_div else ""
        
        # Extract authors
        authors = []
        author_section = soup.find('ul', class_='list--inline')
        if author_section:
            for author_link in author_section.find_all('a'):
                authors.append(author_link.get_text(strip=True))
        
        # Extract DOI if available
        doi = None
        doi_link = soup.find('a', href=lambda x: x and 'doi.org' in x)
        if doi_link:
            doi = doi_link.get('href', '').split('doi.org/')[-1]
        
        return {
            'abstract': abstract,
            'authors': authors,
            'doi': doi
        }
    except Exception as e:
        print(f"Error fetching details: {e}")
        return {'abstract': '', 'authors': [], 'doi': None}

def store_paper(conn, paper_data):
    """Store NBER paper in database"""
    cur = conn.cursor()
    
    try:
        # Domain categorization
        primary_domain, secondary_domains, topics = categorize_paper(
            paper_data['title'],
            paper_data['abstract'],
            []
        )
        
        # Quality scoring - NBER gets automatic boost (prestigious source)
        quality_data = {
            'citation_count': 0,
            'author_h_index_avg': None,
            'publication_status': 'preprint',
            'peer_reviewed': False,
            'journal_impact_factor': None,
            'published_date': paper_data['published_date']
        }
        base_quality = calculate_quality_score(quality_data)
        
        # NBER premium boost: +2 points (extremely prestigious)
        quality_score = min(10.0, base_quality + 2.0)
        
        cur.execute("""
            INSERT INTO papers (
                nber_id, title, authors, abstract, published_date,
                source, source_url, pdf_url, doi,
                primary_domain, secondary_domains, specific_topics,
                publication_status, quality_score, top_institution
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            RETURNING id
        """, (
            paper_data['nber_id'],
            paper_data['title'],
            paper_data['authors'],
            paper_data['abstract'],
            paper_data['published_date'],
            'nber',
            paper_data['url'],
            paper_data.get('pdf_url'),
            paper_data.get('doi'),
            primary_domain,
            secondary_domains,
            topics,
            'preprint',
            quality_score,
            True  # NBER is always top institution
        ))
        
        paper_id = cur.fetchone()[0]
        conn.commit()
        print(f"✅ Stored: {paper_data['title'][:60]}... (ID: {paper_id}, Quality: {quality_score}, Domain: {primary_domain})")
        return paper_id
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error storing paper: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        cur.close()

def scrape_nber_papers(feed_name='all', max_papers=50):
    """Scrape NBER papers from RSS feed"""
    
    conn = get_db_connection()
    if not conn:
        return
    
    feed_url = NBER_RSS_FEEDS.get(feed_name, NBER_RSS_FEEDS['all'])
    
    print(f"🔍 NBER Feed: {feed_name}")
    print(f"📡 {feed_url}\n")
    
    try:
        # Parse RSS feed
        feed = feedparser.parse(feed_url)
        
        if not feed.entries:
            print("No entries found in feed")
            return
        
        print(f"Found {len(feed.entries)} papers in feed\n")
        
        new_papers = 0
        skipped_existing = 0
        skipped_quality = 0
        
        for entry in feed.entries[:max_papers]:
            # Extract paper info from RSS entry
            title = entry.get('title', '')
            url = entry.get('link', '')
            published = entry.get('published_parsed')
            
            nber_id = extract_nber_id(url)
            if not nber_id:
                print(f"⏭️  Skipping - couldn't extract NBER ID from {url}")
                continue
            
            # Check if exists
            if paper_exists(conn, nber_id):
                skipped_existing += 1
                print(f"⏭️  Skipping existing: {nber_id}")
                continue
            
            # Fetch full details
            print(f"Fetching details for: {nber_id}...")
            details = fetch_paper_details(url)
            
            # Parse published date
            pub_date = datetime(*published[:3]).date() if published else datetime.now().date()
            
            paper_data = {
                'nber_id': nber_id,
                'title': title,
                'url': url,
                'pdf_url': f"{url}.pdf",
                'published_date': pub_date,
                **details
            }
            
            paper_id = store_paper(conn, paper_data)
            
            if paper_id:
                new_papers += 1
            else:
                skipped_quality += 1
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()
    
    print(f"\n✅ NBER scraping complete!")
    print(f"   New papers: {new_papers}")
    print(f"   Skipped (existing): {skipped_existing}")
    print(f"   Skipped (low quality): {skipped_quality}")

if __name__ == "__main__":
    feed = sys.argv[1] if len(sys.argv) > 1 else 'all'
    max_papers = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    
    print("=" * 60)
    print("NBER Research Paper Scraper")
    print("=" * 60)
    print()
    
    scrape_nber_papers(feed_name=feed, max_papers=max_papers)
