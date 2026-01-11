import re
import psycopg2
from datetime import datetime
import os

from config import DB_CONFIG

def connect_db():
    return psycopg2.connect(**DB_CONFIG)

def parse_eyberg_file(filepath):
    papers = []
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Split by paper entries (lines starting with ### [)
    entries = re.split(r'\n### ', content)
    
    for entry in entries[1:]: # Skip preamble
        try:
            # Extract common markdown link pattern: [Title](URL)
            title_match = re.search(r'\[(.*?)\]\((.*?)\)', entry)
            if not title_match:
                # Handle special case if start is just [Title](URL) without ### (split removed it)
                title_match = re.search(r'^\[(.*?)\]\((.*?)\)', entry)
                
            if title_match:
                title = title_match.group(1)
                url = title_match.group(2)
                
                # Extract fields
                authors_match = re.search(r'- \*\*Authors:\*\* (.*)', entry)
                journal_match = re.search(r'- \*\*Journal:\*\* (.*)', entry)
                date_match = re.search(r'- \*\*Date:\*\* (.*)', entry)
                
                authors = [a.strip() for a in authors_match.group(1).split(',')] if authors_match else []
                journal = journal_match.group(1).strip() if journal_match else None
                date_str = date_match.group(1).strip() if date_match else None
                
                # Extract PubMed ID from URL
                pubmed_id = None
                if 'pubmed.ncbi.nlm.nih.gov' in url:
                    pm_match = re.search(r'gov/(\d+)', url)
                    if pm_match:
                        pubmed_id = pm_match.group(1)
                
                # Normalize Date
                published_date = None
                if date_str:
                    year_match = re.search(r'\d{4}', date_str)
                    if year_match:
                         published_date = f"{year_match.group(0)}-01-01"
                
                papers.append({
                    'title': title,
                    'source_url': url,
                    'pubmed_id': pubmed_id,
                    'authors': authors,
                    'journal': journal,
                    'published_date': published_date,
                    'source': 'pubmed', # Lowercase to match constraint
                    'author_last_name': 'Eyberg',
                    'abstract': f"Journal: {journal}. Authors: {', '.join(authors)}"
                })
        except Exception as e:
            print(f"Error parsing Eyberg entry: {str(e)[:100]}...")
            
    return papers

def parse_childrights_file(filepath):
    papers = []
    with open(filepath, 'r') as f:
        content = f.read()
        
    entries = re.split(r'\n### ', content)
    
    import hashlib
    
    for entry in entries[1:]:
        try:
            title_match = re.search(r'\[(.*?)\]\((.*?)\)', entry)
            if title_match:
                title = title_match.group(1)
                url = title_match.group(2)
                
                topic_match = re.search(r'- \*\*Topic:\*\* (.*)', entry)
                summary_match = re.search(r'- \*\*Summary:\*\* (.*)', entry)
                
                topic = topic_match.group(1).strip() if topic_match else ""
                summary = summary_match.group(1).strip() if summary_match else ""
                
                # Generate a unique pseudo-ID for the unique constraint
                # We'll use ssrn_id as a container for this custom ID
                pseudo_id = f"crn_{hashlib.md5(title.encode()).hexdigest()[:10]}"
                
                papers.append({
                    'title': title,
                    'source_url': url,
                    'authors': ['Child Rights NGO'],
                    'published_date': '2026-01-01',
                    'source': 'child_rights_ngo',
                    'ssrn_id': pseudo_id, # Hack to satisfy unique(ids) constraint
                    'abstract': f"{summary}\n\nTopic: {topic}",
                    'keywords': [t.strip() for t in topic.split(',')] if topic else []
                })
        except Exception as e:
            print(f"Error parsing ChildRights entry: {str(e)[:100]}")
            
    return papers

def ingest_papers(papers_list):
    conn = connect_db()
    cur = conn.cursor()
    
    added_count = 0
    skipped_count = 0
    
    for paper in papers_list:
        try:
            # Check for dupes by title
            cur.execute("SELECT id FROM papers WHERE title = %s", (paper['title'],))
            if cur.fetchone():
                print(f"Skipping duplicate: {paper['title'][:30]}...")
                skipped_count += 1
                continue
            
            # Prepare SQL
            sql = """
                INSERT INTO papers (
                    title, authors, source, source_url, 
                    pubmed_id, ssrn_id, journal, published_date, 
                    abstract, keywords, quality_score, created_at
                ) VALUES (
                    %s, %s, %s, %s, 
                    %s, %s, %s, %s,
                    %s, %s, %s, NOW()
                )
            """
            
            # Defaults
            authors_arr = paper.get('authors', [])
            keywords_arr = paper.get('keywords', [])
            score = 5.0
            
            cur.execute(sql, (
                paper['title'],
                authors_arr,
                paper['source'],
                paper['source_url'],
                paper.get('pubmed_id'),
                paper.get('ssrn_id'), # Now potentially populated
                paper.get('journal'),
                paper.get('published_date'),
                paper.get('abstract'),
                keywords_arr,
                score
            ))
            added_count += 1
            
        except psycopg2.errors.CheckViolation as e:
            print(f"[INGEST] Constraint Violation: {paper['title'][:30]}... Source '{paper['source']}' invalid.")
            conn.rollback()
            continue
        except Exception as e:
            print(f"[INGEST] Error inserting {paper['title'][:30]}: {e}")
            conn.rollback()
            continue
            
    conn.commit()
    cur.close()
    conn.close()
    
    return added_count, skipped_count

if __name__ == "__main__":
    base_dir = "/Users/rod/Antigravity/home_ai_stack"
    
    print("--- Ingesting Eyberg Papers ---")
    eyberg_file = os.path.join(base_dir, "eyberg_papers.md")
    if os.path.exists(eyberg_file):
        eyberg_papers = parse_eyberg_file(eyberg_file)
        added, skipped = ingest_papers(eyberg_papers)
        print(f"Eyberg: Added {added}, Skipped {skipped}")
    else:
        print("eyberg_papers.md not found")

    print("\n--- Ingesting ChildRightsNGO Articles ---")
    child_file = os.path.join(base_dir, "childrightsngo_papers.md")
    if os.path.exists(child_file):
        child_papers = parse_childrights_file(child_file)
        added, skipped = ingest_papers(child_papers)
        print(f"ChildRights: Added {added}, Skipped {skipped}")
    else:
        print("childrightsngo_papers.md not found")
