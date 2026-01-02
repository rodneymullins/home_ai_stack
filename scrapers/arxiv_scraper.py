#!/usr/bin/env python3
"""
ArXiv Research Paper Scraper (Multi-Source Version)
Fetches economics and quantitative finance papers from ArXiv
"""

import arxiv
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scrapers.domain_categorizer import categorize_paper, get_source_categories
from scrapers.paper_quality import calculate_quality_score, should_store_paper, get_author_affiliations

# Use Thor's database connection
import psycopg2

DB_CONFIG = {'database': 'research_papers', 'user': 'rod', 'host': '192.168.1.211'}

# PDF storage path
PDF_STORAGE_PATH = Path('/mnt/raid0/research_papers/pdfs/arxiv')
PDF_STORAGE_PATH.mkdir(parents=True, exist_ok=True)

# ArXiv categories to scrape
CATEGORIES = ['econ.*', 'q-fin.*']

def get_db_connection():
    """Get database connection to research_papers DB"""
    try:
        return psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

def paper_exists(conn, arxiv_id):
    """Check if paper already exists"""
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM papers WHERE arxiv_id = %s", (arxiv_id,))
    exists = cur.fetchone() is not None
    cur.close()
    return exists

def store_paper(conn, paper, pdf_path=None):
    """Store paper in database with domain categorization and quality scoring"""
    cur = conn.cursor()
    
    try:
        arxiv_id = paper.entry_id.split('/')[-1]
        
        # Get source categories (already strings in new arxiv package)
        source_cats = [str(cat) for cat in paper.categories]
        
        # Domain categorization
        primary_domain, secondary_domains, topics = categorize_paper(
            paper.title,
            paper.summary,
            source_cats
        )
        
        # Author affiliations
        affiliations = get_author_affiliations(paper.authors)
        top_inst = len(affiliations) > 0
        
        # Quality scoring
        paper_data = {
            'citation_count': 0,  # Will be enriched by Semantic Scholar later
            'author_h_index_avg': None,  # Will be enriched later
            'publication_status': 'preprint',
            'peer_reviewed': False,
            'journal_impact_factor': None,
            'published_date': paper.published
        }
        quality_score = calculate_quality_score(paper_data)
        
        # Only store if meets minimum quality threshold
        if not should_store_paper(paper_data):
            print(f"⏭️  Skipping low quality: {paper.title[:50]}... (score: {quality_score})")
            return None
        
        cur.execute("""
            INSERT INTO papers (
                arxiv_id, title, authors, abstract, published_date, updated_date,
                source, source_url, pdf_url, pdf_path,
                primary_domain, secondary_domains, specific_topics,
                publication_status, peer_reviewed, quality_score,
                author_affiliations, top_institution
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s
            )
            RETURNING id
        """, (
            arxiv_id,
            paper.title,
            [author.name for author in paper.authors],
            paper.summary,
            paper.published.date(),
            paper.updated.date() if paper.updated else None,
            'arxiv',
            paper.entry_id,
            paper.pdf_url,
            str(pdf_path) if pdf_path else None,
            primary_domain,
            secondary_domains,
            topics,
            'preprint',
            False,
            quality_score,
            affiliations,
            top_inst
        ))
        
        paper_id = cur.fetchone()[0]
        conn.commit()
        print(f"✅ Stored: {paper.title[:60]}... (ID: {paper_id}, Quality: {quality_score}, Domain: {primary_domain})")
        return paper_id
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error storing paper: {e}")
        return None
    finally:
        cur.close()

def download_pdf(paper, arxiv_id):
    """Download paper PDF"""
    try:
        pdf_filename = f"{arxiv_id.replace('/', '_')}.pdf"
        pdf_path = PDF_STORAGE_PATH / pdf_filename
        
        if pdf_path.exists():
            return pdf_path
        
        paper.download_pdf(filename=str(pdf_path))
        print(f"📥 Downloaded: {pdf_filename}")
        return pdf_path
    except Exception as e:
        print(f"❌ PDF download failed: {e}")
        return None

def scrape_arxiv_papers(days_back=7, max_results=100):
    """Scrape ArXiv papers"""
    conn = get_db_connection()
    if not conn:
        return
    
    date_filter = (datetime.now() - timedelta(days=days_back)).strftime('%Y%m%d')
    query_parts = [f"cat:{cat}" for cat in CATEGORIES]
    query = f"({' OR '.join(query_parts)}) AND submittedDate:[{date_filter}0000 TO 99991231]"
    
    print(f"🔍 ArXiv Query: {query}")
    print(f"📅 Last {days_back} days\n")
    
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending
    )
    
    new_papers = 0
    skipped = 0
    
    try:
        for paper in search.results():
            arxiv_id = paper.entry_id.split('/')[-1]
            
            # Skip if already exists
            if paper_exists(conn, arxiv_id):
                skipped += 1
                print(f"⏭️  Skipping existing: {arxiv_id}")
                continue
            
            # Download PDF
            pdf_path = download_pdf(paper, arxiv_id)
            
            # Store in database
            paper_id = store_paper(conn, paper, pdf_path)
            
            if paper_id:
                new_papers += 1
            
    except Exception as e:
        print(f"❌ Scraping error: {e}")
    
    finally:
        conn.close()
    
    print(f"\n✅ Scraping complete!")
    print(f"   New papers: {new_papers}")
    print(f"   Skipped (existing): {skipped}")

if __name__ == "__main__":
    import sys
    
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    max_results = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    
    print("=" * 60)
    print("ArXiv Research Paper Scraper")
    print("=" * 60)
    
    scrape_arxiv_papers(days_back=days, max_results=max_results)
