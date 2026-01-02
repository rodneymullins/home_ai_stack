#!/usr/bin/env python3
"""
Research Paper Mem0 Integration
Stores papers in Mem0 for RAG/semantic search via Open Web UI
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mem0 import Memory
import psycopg2
from datetime import datetime

# Database config
DB_CONFIG = {'database': 'research_papers', 'user': 'rod', 'host': '192.168.1.211'}

# Initialize Mem0
memory = Memory()

def get_db_connection():
    """Get database connection"""
    try:
        return psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        print(f"Database error: {e}")
        return None

def store_paper_in_mem0(paper_id, title, authors, abstract, primary_domain, topics, source):
    """Store a research paper in Mem0 for RAG"""
    
    # Create rich memory text
    authors_str = ', '.join(authors[:3])  # First 3 authors
    topics_str = ', '.join(topics[:5]) if topics else 'general'
    
    memory_text = f"""
Research Paper: {title}

Authors: {authors_str}
Domain: {primary_domain}
Topics: {topics_str}
Source: {source}

Abstract:
{abstract}
"""
    
    try:
        # Store in Mem0
        result = memory.add(
            memory_text,
            user_id="research_papers",
            metadata={
                "type": "research_paper",
                "paper_id": paper_id,
                "title": title,
                "domain": primary_domain,
                "topics": topics,
                "source": source
            }
        )
        
        return result
        
    except Exception as e:
        print(f"Mem0 error for paper {paper_id}: {e}")
        return None

def sync_papers_to_mem0(limit=None):
    """Sync papers from database to Mem0"""
    
    conn = get_db_connection()
    if not conn:
        return
    
    try:
        cur = conn.cursor()
        
        # Get papers not yet in Mem0
        query = """
            SELECT id, title, authors, abstract, primary_domain, 
                   specific_topics, source
            FROM papers 
            WHERE mem0_stored = FALSE
            ORDER BY id DESC
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        cur.execute(query)
        papers = cur.fetchall()
        
        print(f"Found {len(papers)} papers to sync to Mem0\n")
        
        synced = 0
        for paper in papers:
            paper_id, title, authors, abstract, domain, topics, source = paper
            
            print(f"Syncing: {title[:60]}...")
            
            result = store_paper_in_mem0(
                paper_id, title, authors or [], abstract, 
                domain, topics or [], source
            )
            
            if result:
                # Mark as stored in Mem0
                cur.execute(
                    "UPDATE papers SET mem0_stored = TRUE WHERE id = %s",
                    (paper_id,)
                )
                conn.commit()
                synced += 1
                print(f"✅ Synced to Mem0 (ID: {paper_id})")
            else:
                print(f"❌ Failed to sync")
            
        print(f"\n✅ Sync complete! {synced}/{len(papers)} papers stored in Mem0")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

def search_papers(query, limit=5):
    """Search papers using Mem0"""
    try:
        results = memory.search(
            query,
            user_id="research_papers",
            limit=limit
        )
        
        return results
    except Exception as e:
        print(f"Search error: {e}")
        return []

if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    
    print("=" * 60)
    print("Research Paper Mem0 Integration")
    print("=" * 60)
    print()
    
    if len(sys.argv) > 1 and sys.argv[1] == "search":
        # Search mode
        query = " ".join(sys.argv[2:])
        print(f"Searching for: {query}\n")
        results = search_papers(query)
        
        for i, result in enumerate(results, 1):
            print(f"{i}. {result.get('memory', '')[:100]}...")
            print(f"   Relevance: {result.get('score', 0):.2f}\n")
    else:
        # Sync mode
        sync_papers_to_mem0(limit=limit)
