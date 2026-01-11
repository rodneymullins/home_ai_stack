#!/usr/bin/env python3
"""
Ingest Joshi Parental Alienation Articles into Research Papers Database
"""

import psycopg2
from datetime import datetime
import hashlib
from config import RESEARCH_DB_CONFIG

def generate_semantic_id(title, author):
    content = f"{title}_{author}".lower()
    return f"joshi_{hashlib.md5(content.encode()).hexdigest()[:12]}"

# Format: (title, authors[], journal, year, month, url, domain, topics[])
ARTICLES = [
    ("False Positives of Parental Alienation in Child Custody Evaluations", ["Ashish S. Joshi"], "Michigan Family Law Journal", 2024, 6, "https://www.joshiattorneys.com/insights/", "Psychology", ["Parental Alienation", "Child Custody", "False Positives"]),
    ("ABCs of Parental Alienation for Defense Attorneys Who Defend False Allegations of Abuse", ["Ashish S. Joshi", "Alan Blotcky"], "The Champion (NACDL)", 2023, 11, "https://www.nacdl.org/champion", "Law", ["Parental Alienation", "False Allegations", "Defense"]),
    ("On a Sticky Wicket: Representing the Best Interests of Brainwashed and Programmed Children in High-Conflict Child Custody Cases", ["Ashish S. Joshi"], "Litigation (ABA)", 2023, 9, "https://www.joshiattorneys.com/insights/", "Law", ["Parental Alienation", "Child Custody", "Brainwashing"]),
    ("Coercive Control: What Family Practitioners Should Know About This Insidious Form of Mental Abuse", ["Ashish S. Joshi"], "Michigan Family Law Journal", 2021, 11, "https://www.joshiattorneys.com/insights/", "Psychology", ["Coercive Control", "Mental Abuse", "Family Law"]),
    ("Leave No Child Behind: Parental Alienation in Family Courts", ["Ashish S. Joshi"], "Litigation (ABA)", 2021, 7, "https://www.joshiattorneys.com/insights/", "Law", ["Parental Alienation", "Family Courts"]),
    ("A is for Alienation: Tips for Litigating Parental Alienation in Custody Battles", ["Ashish S. Joshi"], "NYSBA Family Law Review", 2021, 1, "https://nysba.org/publications/", "Law", ["Parental Alienation", "Litigation", "Custody"]),
    ("Parental Alienation is Real: Exposing the Myth of the Woozle", ["Ashish S. Joshi"], "Litigation (ABA)", 2021, 3, "https://www.joshiattorneys.com/insights/", "Psychology", ["Parental Alienation", "Research", "Woozle Effect"]),
    ("Cases of Parental Alienation in Pennsylvania's Family Courts", ["Ashish S. Joshi"], "The Pennsylvania Lawyer", 2021, 3, "https://www.pabar.org/publications/", "Law", ["Parental Alienation", "Pennsylvania", "Case Law"]),
    ("Parental Alienation and Domestic Violence: Two Parts of the Same Coin (Part 2)", ["Ashish S. Joshi"], "Michigan Family Law Journal", 2020, 12, "https://www.joshiattorneys.com/insights/", "Psychology", ["Parental Alienation", "Domestic Violence"]),
    ("Litigating Parental Alienation Cases: The Good, the Bad, and the Ugly", ["Ashish S. Joshi"], "Parental Alienation International", 2020, 11, "https://pasg.info/", "Law", ["Parental Alienation", "Litigation", "Best Practices"]),
    ("Parental Alienation: India Joins Family Courts Around the World to Fight Child Emotional Abuse", ["Ashish S. Joshi"], "Legal Era", 2020, 11, "https://www.legaleraonline.com/", "Law", ["Parental Alienation", "India", "International"]),
    ("Parental Alienation and Domestic Violence: Two Parts of the Same Coin (Part 1)", ["Ashish S. Joshi"], "Michigan Family Law Journal", 2020, 10, "https://www.joshiattorneys.com/insights/", "Psychology", ["Parental Alienation", "Domestic Violence"]),
    ("Temporary No-Contact Order: The Necessary Ingredient for Effective Reunification in Cases Involving Parental Alienation", ["Ashish S. Joshi"], "Michigan Family Law Journal", 2020, 2, "https://www.joshiattorneys.com/insights/", "Law", ["Parental Alienation", "Reunification", "No-Contact"]),
    ("Parental Alienation and the Role of GALs and LGALs (Parts 1 & 2)", ["Ashish S. Joshi"], "Michigan Family Law Journal", 2018, 8, "https://www.joshiattorneys.com/insights/", "Law", ["Parental Alienation", "Guardian ad Litem", "Child Advocacy"]),
    ("Parental Alienation: Remedies", ["Ashish S. Joshi"], "Michigan Family Law Journal", 2016, 11, "https://www.michbar.org/family", "Law", ["Parental Alienation", "Remedies", "Treatment"]),
    ("Parental Alienation: The Problem", ["Ashish S. Joshi"], "Michigan Family Law Journal", 2016, 10, "https://www.michbar.org/family", "Psychology", ["Parental Alienation", "Definition", "Overview"]),
    ("Taint Hearing: Scientific and Legal Underpinnings", ["Ashish S. Joshi"], "The Champion (NACDL)", 2010, 11, "https://www.nacdl.org/champion", "Law", ["Child Testimony", "Taint Hearing", "Suggestibility"]),
]

def ingest_articles():
    conn = psycopg2.connect(**RESEARCH_DB_CONFIG)
    cur = conn.cursor()
    
    ingested = 0
    skipped = 0
    
    for title, authors, journal, year, month, url, domain, topics in ARTICLES:
        # Check if exists
        cur.execute("SELECT id FROM papers WHERE title = %s", (title,))
        if cur.fetchone():
            print(f"[INGEST] Skipped: {title[:50]}...")
            skipped += 1
            continue
        
        semantic_id = generate_semantic_id(title, authors[0])
        published_date = f"{year}-{month:02d}-01"
        
        cur.execute("""
            INSERT INTO papers (
                semantic_scholar_id, doi, title, authors, journal, published_date,
                source, source_url, primary_domain, specific_topics, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (semantic_id, f"10.99999/{semantic_id}", title, authors, journal, published_date, 
              "web_scrape", url, domain, topics, datetime.now()))
        
        print(f"[INGEST] Added: {title[:50]}...")
        ingested += 1
    
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"\n[INGEST] Summary: {ingested} added, {skipped} skipped")

if __name__ == "__main__":
    print("[INGEST] Starting Joshi Articles Ingestion...")
    print(f"[INGEST] Total: {len(ARTICLES)} articles")
    ingest_articles()
