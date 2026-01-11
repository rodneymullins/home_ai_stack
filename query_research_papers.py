#!/usr/bin/env python3
"""
Research Paper Database Query Tool
Quick access to paper statistics and searching
"""

import psycopg2
from datetime import datetime

DB_CONFIG = {'database': 'wealth', 'user': 'rod', 'host': '192.168.1.211'}

def get_stats():
    """Get overall paper statistics"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    # Overall stats
    cur.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(DISTINCT primary_domain) as domains,
            COUNT(DISTINCT source) as sources,
            ROUND(AVG(quality_score), 2) as avg_quality,
            MIN(published_date) as oldest,
            MAX(published_date) as newest
        FROM papers
    """)
    
    stats = cur.fetchone()
    
    print("=" * 70)
    print("RESEARCH PAPER DATABASE STATS")
    print("=" * 70)
    print(f"Total Papers: {stats[0]}")
    print(f"Unique Domains: {stats[1]}")
    print(f"Sources: {stats[2]}")
    print(f"Average Quality: {stats[3]}/10")
    print(f"Date Range: {stats[4]} to {stats[5]}")
    
    # By source
    print(f"\n📚 BY SOURCE:")
    cur.execute("""
        SELECT source, COUNT(*) as count, ROUND(AVG(quality_score), 2) as avg_quality
        FROM papers
        GROUP BY source
        ORDER BY count DESC
    """)
    
    for row in cur.fetchall():
        print(f"  {row[0]:15} {row[1]:4} papers  (avg quality: {row[2]})")
    
    # By domain
    print(f"\n🏷️  BY DOMAIN:")
    cur.execute("""
        SELECT primary_domain, COUNT(*) as count
        FROM papers
        GROUP BY primary_domain
        ORDER BY count DESC
        LIMIT 10
    """)
    
    for row in cur.fetchall():
        print(f"  {row[0]:30} {row[1]:4} papers")
    
    # Recent papers
    print(f"\n🆕 RECENT ADDITIONS (last 7 days):")
    cur.execute("""
        SELECT title, source, published_date, quality_score
        FROM papers
        WHERE created_at > NOW() - INTERVAL '7 days'
        ORDER BY created_at DESC
        LIMIT 5
    """)
    
    for row in cur.fetchall():
        print(f"  [{row[1]}] {row[0][:60]}... (Q:{row[3]})")
    
    # High quality papers
    print(f"\n⭐ TOP QUALITY PAPERS (score ≥ 7):")
    cur.execute("""
        SELECT title, source, quality_score
        FROM papers
        WHERE quality_score >= 7
        ORDER BY quality_score DESC, published_date DESC
        LIMIT 5
    """)
    
    for row in cur.fetchall():
        print(f"  [{row[1]}] {row[0][:60]}... (Q:{row[2]})")
    
    cur.close()
    conn.close()
    print("\n" + "=" * 70)

def search_papers(query):
    """Search papers by title or abstract"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT title, authors, source, quality_score, published_date
        FROM papers
        WHERE title ILIKE %s OR abstract ILIKE %s
        ORDER BY quality_score DESC, published_date DESC
        LIMIT 10
    """, (f'%{query}%', f'%{query}%'))
    
    results = cur.fetchall()
    
    if results:
        print(f"\n🔍 Found {len(results)} papers matching '{query}':\n")
        for row in results:
            print(f"Title: {row[0]}")
            print(f"Authors: {row[1][:3] if len(row[1]) > 3 else row[1]}")
            print(f"Source: {row[2]} | Quality: {row[3]} | Date: {row[4]}")
            print("-" * 70)
    else:
        print(f"No papers found matching '{query}'")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Search mode
        search_papers(' '.join(sys.argv[1:]))
    else:
        # Stats mode
        get_stats()
