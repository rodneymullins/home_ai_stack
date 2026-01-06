#!/usr/bin/env python3
"""
SSRN CSV Import Tool
Imports manually exported SSRN search results into the research database

Since SSRN doesn't provide API access and blocks scraping, this tool allows
users to manually search SSRN, export results as CSV, and import them.

Usage:
    1. Search SSRN for papers (https://www.ssrn.com)
    2. Export results to CSV
    3. Run: python3 ssrn_csv_import.py <csv_file>
"""

import csv
import sys
import os
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scrapers.domain_categorizer import categorize_paper
from scrapers.paper_quality import calculate_quality_score, should_store_paper

import psycopg2

DB_CONFIG = {'database': 'research_papers', 'user': 'rod', 'host': '192.168.1.211'}

def get_db_connection():
    """Get database connection"""
    try:
        return psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

def paper_exists(conn, ssrn_id=None, doi=None, title=None):
    """Check if paper already exists"""
    cur = conn.cursor()
    
    if ssrn_id:
        cur.execute("SELECT 1 FROM papers WHERE ssrn_id = %s", (ssrn_id,))
        if cur.fetchone():
            cur.close()
            return True
    
    if doi:
        cur.execute("SELECT 1 FROM papers WHERE doi = %s", (doi,))
        if cur.fetchone():
            cur.close()
            return True
    
    if title:
        cur.execute("SELECT 1 FROM papers WHERE title = %s", (title,))
        if cur.fetchone():
            cur.close()
            return True
    
    cur.close()
    return False

def parse_ssrn_date(date_str):
    """Parse SSRN date formats"""
    if not date_str:
        return None
    
    formats = [
        '%B %d, %Y',      # December 30, 2024
        '%Y-%m-%d',       # 2024-12-30
        '%m/%d/%Y',       # 12/30/2024
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except:
            continue
    
    return None

def store_paper(conn, row):
    """Store SSRN paper from CSV row"""
    cur = conn.cursor()
    
    try:
        # Extract SSRN ID from URL if available
        ssrn_id = None
        if 'url' in row or 'URL' in row:
            url = row.get('url') or row.get('URL', '')
            if 'abstract_id=' in url:
                ssrn_id = url.split('abstract_id=')[1].split('&')[0]
        
        # Try ssrn_id column directly
        if not ssrn_id and 'ssrn_id' in row:
            ssrn_id = row['ssrn_id']
        
        # Basic fields (different CSV formats)
        title = row.get('title') or row.get('Title') or row.get('Paper Title', '')
        abstract = row.get('abstract') or row.get('Abstract', '')
        
        # Authors (may be comma-separated string)
        authors_str = row.get('authors') or row.get('Authors') or row.get('Author', '')
        authors = [a.strip() for a in authors_str.split(',') if a.strip()] if authors_str else []
        
        # Parse date
        date_str = row.get('date') or row.get('Date') or row.get('Posted Date', '')
        pub_date = parse_ssrn_date(date_str)
        
        # DOI if available
        doi = row.get('doi') or row.get('DOI')
        
        # Downloads/views as proxy for quality
        downloads = 0
        if 'downloads' in row or 'Downloads' in row:
            try:
                downloads = int(row.get('downloads') or row.get('Downloads', 0))
            except:
                pass
        
        # Check if exists
        if paper_exists(conn, ssrn_id, doi, title):
            print(f"⏭️  Skipping existing: {title[:50]}...")
            return None
        
        # Domain categorization
        primary_domain, secondary_domains, topics = categorize_paper(
            title,
            abstract,
            []
        )
        
        # Quality scoring
        # SSRN gets slight boost (+0.5) as reputable source
        quality_data = {
            'citation_count': downloads // 100,  # Rough proxy: 100 downloads ~ 1 citation
            'author_h_index_avg': None,
            'publication_status': 'preprint',
            'peer_reviewed': False,
            'journal_impact_factor': None,
            'published_date': pub_date
        }
        quality_score = min(10.0, calculate_quality_score(quality_data) + 0.5)
        
        if not should_store_paper(quality_data):
            print(f"⏭️  Skipping low quality: {title[:50]}... (score: {quality_score})")
            return None
        
        cur.execute("""
            INSERT INTO papers (
                ssrn_id, doi, title, authors, abstract, published_date,
                source, source_url,
                primary_domain, secondary_domains, specific_topics,
                publication_status, quality_score
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            RETURNING id
        """, (
            ssrn_id,
            doi,
            title,
            authors,
            abstract,
            pub_date,
            'ssrn',
            f"https://ssrn.com/abstract={ssrn_id}" if ssrn_id else None,
            primary_domain,
            secondary_domains,
            topics,
            'preprint',
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

def import_ssrn_csv(csv_file):
    """Import SSRN papers from CSV file"""
    conn = get_db_connection()
    if not conn:
        return
    
    print(f"📁 Importing from: {csv_file}\n")
    
    new_papers = 0
    skipped_existing = 0
    skipped_quality = 0
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                paper_id = store_paper(conn, row)
                
                if paper_id:
                    new_papers += 1
                elif 'Skipping existing' in str(paper_id):
                    skipped_existing += 1
                else:
                    skipped_quality += 1
                    
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()
    
    print(f"\n✅ SSRN CSV import complete!")
    print(f"   New papers: {new_papers}")
    print(f"   Skipped (existing): {skipped_existing}")
    print(f"   Skipped (low quality): {skipped_quality}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 ssrn_csv_import.py <csv_file>")
        print("\nHow to export from SSRN:")
        print("1. Search SSRN: https://www.ssrn.com")
        print("2. Click 'Export to CSV' or save search results")
        print("3. Run this script with the CSV file")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    
    if not Path(csv_file).exists():
        print(f"❌ File not found: {csv_file}")
        sys.exit(1)
    
    print("=" * 60)
    print("SSRN CSV Import Tool")
    print("=" * 60)
    print()
    
    import_ssrn_csv(csv_file)
