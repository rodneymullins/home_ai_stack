#!/usr/bin/env python3
"""
PsyArXiv Research Paper Scraper
Fetches psychology preprints from PsyArXiv via OSF API
"""

import requests
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
import time

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scrapers.domain_categorizer import categorize_paper
from scrapers.paper_quality import calculate_quality_score, should_store_paper, get_author_affiliations

import psycopg2

DB_CONFIG = {'database': 'research_papers', 'user': 'rod', 'host': '192.168.1.211'}

# PDF storage path
PDF_STORAGE_PATH = Path('/mnt/raid0/research_papers/pdfs/psyarxiv')
PDF_STORAGE_PATH.mkdir(parents=True, exist_ok=True)

# PsyArXiv OSF API - Using general preprints endpoint with provider filter
PSYARXIV_API = "https://api.osf.io/v2/preprints/"

def get_db_connection():
    """Get database connection"""
    try:
        return psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

def paper_exists(conn, psyarxiv_id):
    """Check if paper already exists"""
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM papers WHERE psyarxiv_id = %s", (psyarxiv_id,))
    exists = cur.fetchone() is not None
    cur.close()
    return exists

def store_paper(conn, preprint_data, pdf_path=None):
    """Store PsyArXiv paper in database"""
    cur = conn.cursor()
    
    try:
        # Extract metadata
        psyarxiv_id = preprint_data['id']
        attributes = preprint_data['attributes']
        
        title = attributes.get('title', '')
        abstract = attributes.get('description', '')
        
        # Get contributors (authors)
        contributors = preprint_data.get('relationships', {}).get('contributors', {}).get('links', {})
        authors_list = []  # Simplified for now
        
        published_date = datetime.fromisoformat(attributes['date_published'].replace('Z', '+00:00')).date()
        
        # Domain categorization
        # Subjects are nested arrays: [[{id, text}, {id, text}], [...]]
        subjects = attributes.get('subjects', [])
        subject_names = []
        if subjects:
            for subject_group in subjects:
                if isinstance(subject_group, list):
                    subject_names.extend([s.get('text', '') for s in subject_group if isinstance(s, dict)])
        
        primary_domain, secondary_domains, topics = categorize_paper(
            title,
            abstract,
            subject_names
        )
        
        # Quality scoring
        paper_data = {
            'citation_count': 0,
            'author_h_index_avg': None,
            'publication_status': 'preprint',
            'peer_reviewed': False,
            'published_date': published_date
        }
        quality_score = calculate_quality_score(paper_data)
        
        if not should_store_paper(paper_data):
            print(f"⏭️  Skipping low quality: {title[:50]}...")
            return None
        
        # Get PDF URL
        pdf_url = preprint_data.get('links', {}).get('preprint_doi', '')
        
        cur.execute("""
            INSERT INTO papers (
                psyarxiv_id, title, authors, abstract, published_date,
                source, source_url, pdf_url, pdf_path,
                primary_domain, secondary_domains, specific_topics,
                publication_status, peer_reviewed, quality_score
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            RETURNING id
        """, (
            psyarxiv_id,
            title,
            authors_list,
            abstract,
            published_date,
            'psyarxiv',
            f"https://osf.io/preprints/psyarxiv/{psyarxiv_id}",
            pdf_url,
            str(pdf_path) if pdf_path else None,
            primary_domain,
            secondary_domains,
            topics,
            'preprint',
            False,
            quality_score
        ))
        
        paper_id = cur.fetchone()[0]
        conn.commit()
        print(f"✅ Stored: {title[:60]}... (ID: {paper_id}, Quality: {quality_score}, Domain: {primary_domain})")
        return paper_id
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error storing paper: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        cur.close()

def scrape_psyarxiv_papers(days_back=7, max_results=100):
    """Scrape PsyArXiv preprints"""
    conn = get_db_connection()
    if not conn:
        return
    
    # Calculate date filter
    date_filter = (datetime.now() - timedelta(days=days_back)).isoformat()
    
    params = {
        'filter[provider]': 'psyarxiv',  # Filter for PsyArXiv preprints only
        'filter[date_modified][gte]': date_filter,
        'page[size]': min(max_results, 100)  # API max is 100 per page
    }
    
    print(f"🔍 PsyArXiv API Query")
    print(f"📅 Last {days_back} days\n")
    
    new_papers = 0
    skipped_existing = 0
    skipped_quality = 0
    
    try:
        response = requests.get(PSYARXIV_API, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        preprints = data.get('data', [])
        print(f"Found {len(preprints)} preprints\n")
        
        for preprint in preprints:
            psyarxiv_id = preprint['id']
            
            if paper_exists(conn, psyarxiv_id):
                skipped_existing += 1
                continue
            
            paper_id = store_paper(conn, preprint)
            
            if paper_id:
                new_papers += 1
            else:
                skipped_quality += 1
            
            time.sleep(0.5)  # Be polite to API
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()
    
    print(f"\n✅ PsyArXiv scraping complete!")
    print(f"   New papers: {new_papers}")
    print(f"   Skipped (existing): {skipped_existing}")
    print(f"   Skipped (low quality): {skipped_quality}")

if __name__ == "__main__":
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    max_results = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    
    print("=" * 60)
    print("PsyArXiv Research Paper Scraper")
    print("=" * 60)
    
    scrape_psyarxiv_papers(days_back=days, max_results=max_results)
