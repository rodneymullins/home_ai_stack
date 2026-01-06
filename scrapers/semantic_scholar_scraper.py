#!/usr/bin/env python3
"""
Semantic Scholar Research Paper Scraper
Fetches papers from Semantic Scholar API with citation data

Semantic Scholar provides:
- 200M+ academic papers across all fields
- Citation counts and influence scores
- Cross-indexed papers (ArXiv, SSRN, PubMed, etc.)
- Free API access (rate limited)
"""

import requests
import sys
import os
from datetime import datetime
from pathlib import Path
import time

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scrapers.domain_categorizer import categorize_paper
from scrapers.paper_quality import calculate_quality_score, should_store_paper

import psycopg2

DB_CONFIG = {'database': 'research_papers', 'user': 'rod', 'host': '192.168.1.211'}

# Semantic Scholar API
SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1"

# Rate limiting: 100 requests per 5 minutes
REQUEST_DELAY = 3.5  # seconds between requests to stay well under limit

def get_db_connection():
    """Get database connection"""
    try:
        return psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

def paper_exists(conn, semantic_scholar_id=None, doi=None, arxiv_id=None):
    """Check if paper already exists by any identifier"""
    cur = conn.cursor()
    
    if semantic_scholar_id:
        cur.execute("SELECT 1 FROM papers WHERE semantic_scholar_id = %s", (semantic_scholar_id,))
        if cur.fetchone():
            cur.close()
            return True
    
    if doi:
        cur.execute("SELECT 1 FROM papers WHERE doi = %s", (doi,))
        if cur.fetchone():
            cur.close()
            return True
    
    if arxiv_id:
        cur.execute("SELECT 1 FROM papers WHERE arxiv_id = %s", (arxiv_id,))
        if cur.fetchone():
            cur.close()
            return True
    
    cur.close()
    return False

def store_paper(conn, paper_data):
    """Store Semantic Scholar paper in database"""
    cur = conn.cursor()
    
    try:
        # Extract metadata
        paper_id = paper_data['paperId']
        title = paper_data.get('title', '')
        abstract = paper_data.get('abstract', '')
        
        # Authors
        authors = [author.get('name', '') for author in paper_data.get('authors', [])]
        
        # Publication info
        year = paper_data.get('year')
        pub_date = datetime(year, 1, 1).date() if year else None
        venue = paper_data.get('venue', '')
        
        # External IDs
        external_ids = paper_data.get('externalIds', {})
        doi = external_ids.get('DOI')
        arxiv_id = external_ids.get('ArXiv')
        pubmed_id = external_ids.get('PubMed')
        
        # Citation metrics
        citation_count = paper_data.get('citationCount', 0)
        influential_citation_count = paper_data.get('influentialCitationCount', 0)
        
        # Determine source based on external IDs
        if arxiv_id:
            source = 'arxiv'
        elif pubmed_id:
            source = 'pubmed'
        else:
            source = 'semantic'
        
        # Domain categorization
        primary_domain, secondary_domains, topics = categorize_paper(
            title,
            abstract,
            []
        )
        
        # Quality scoring with citation data
        quality_data = {
            'citation_count': citation_count,
            'author_h_index_avg': None,  # Could enrich later
            'publication_status': 'published' if venue else 'preprint',
            'peer_reviewed': bool(venue),
            'journal_impact_factor': None,
            'published_date': pub_date
        }
        quality_score = calculate_quality_score(quality_data)
        
        # Boost for influential citations
        if influential_citation_count > 0:
            influence_boost = min(1.0, influential_citation_count / 10)
            quality_score = min(10.0, quality_score + influence_boost)
        
        if not should_store_paper(quality_data):
            print(f"⏭️  Skipping low quality: {title[:50]}... (score: {quality_score})")
            return None
        
        # PDF URL
        pdf_url = paper_data.get('openAccessPdf', {}).get('url') if paper_data.get('openAccessPdf') else None
        
        cur.execute("""
            INSERT INTO papers (
                semantic_scholar_id, doi, arxiv_id, pubmed_id,
                title, authors, abstract, published_date,
                source, source_url, pdf_url,
                primary_domain, secondary_domains, specific_topics,
                publication_status, peer_reviewed, quality_score,
                citation_count, influence_score, journal
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            RETURNING id
        """, (
            paper_id,
            doi,
            arxiv_id,
            pubmed_id,
            title,
            authors,
            abstract,
            pub_date,
            source,
            f"https://www.semanticscholar.org/paper/{paper_id}",
            pdf_url,
            primary_domain,
            secondary_domains,
            topics,
            'published' if venue else 'preprint',
            bool(venue),
            quality_score,
            citation_count,
            float(influential_citation_count) if influential_citation_count else None,
            venue
        ))
        
        db_paper_id = cur.fetchone()[0]
        conn.commit()
        print(f"✅ Stored: {title[:60]}... (ID: {db_paper_id}, Citations: {citation_count}, Quality: {quality_score}, Domain: {primary_domain})")
        return db_paper_id
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error storing paper: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        cur.close()

def search_papers(query, fields_of_study=None, min_citations=0, year_from=None, max_results=100):
    """
    Search Semantic Scholar for papers
    
    Args:
        query: Search query string
        fields_of_study: List of fields (e.g., ['Economics', 'Computer Science'])
        min_citations: Minimum citation count filter
        year_from: Only papers published from this year onwards
        max_results: Maximum number of results to return
    """
    conn = get_db_connection()
    if not conn:
        return
    
    url = f"{SEMANTIC_SCHOLAR_API}/paper/search"
    
    # Build query parameters
    params = {
        'query': query,
        'fields': 'paperId,externalIds,title,authors,abstract,year,venue,citationCount,influentialCitationCount,openAccessPdf',
        'limit': min(100, max_results)  # API max is 100 per request
    }
    
    if fields_of_study:
        params['fieldsOfStudy'] = ','.join(fields_of_study)
    
    if year_from:
        params['year'] = f"{year_from}-"
    
    print(f"🔍 Semantic Scholar Query: {query}")
    if fields_of_study:
        print(f"📚 Fields: {', '.join(fields_of_study)}")
    if min_citations > 0:
        print(f"📊 Min Citations: {min_citations}")
    print()
    
    new_papers = 0
    skipped_existing = 0
    skipped_quality = 0
    
    offset = 0
    total_fetched = 0
    
    try:
        while total_fetched < max_results:
            params['offset'] = offset
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            papers = data.get('data', [])
            if not papers:
                break
            
            print(f"Fetched {len(papers)} papers (offset {offset})...")
            
            for paper in papers:
                # Filter by minimum citations
                if paper.get('citationCount', 0) < min_citations:
                    continue
                
                # Check if exists
                paper_id = paper.get('paperId')
                external_ids = paper.get('externalIds', {})
                
                if paper_exists(conn, paper_id, external_ids.get('DOI'), external_ids.get('ArXiv')):
                    skipped_existing += 1
                    continue
                
                # Store paper
                db_id = store_paper(conn, paper)
                
                if db_id:
                    new_papers += 1
                else:
                    skipped_quality += 1
                
                # Rate limiting
                time.sleep(REQUEST_DELAY)
            
            total_fetched += len(papers)
            offset += len(papers)
            
            # Check if we have more results
            if len(papers) < 100:
                break
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()
    
    print(f"\n✅ Semantic Scholar scraping complete!")
    print(f"   New papers: {new_papers}")
    print(f"   Skipped (existing): {skipped_existing}")
    print(f"   Skipped (low quality): {skipped_quality}")

if __name__ == "__main__":
    # Example: Search for economics papers with at least 10 citations from 2020 onwards
    query = sys.argv[1] if len(sys.argv) > 1 else "behavioral economics OR financial economics"
    min_citations = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    max_results = int(sys.argv[3]) if len(sys.argv) > 3 else 50
    
    print("=" * 60)
    print("Semantic Scholar Research Paper Scraper")
    print("=" * 60)
    print()
    
    search_papers(
        query=query,
        fields_of_study=['Economics', 'Business'],
        min_citations=min_citations,
        year_from=2020,
        max_results=max_results
    )
