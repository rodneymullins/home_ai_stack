import psycopg2
import hashlib

from config import DB_CONFIG

PAPERS_TO_INGEST = [
    # Seminal / Critical Works
    {
        "title": "The 'solution' to parental alienation: A critique of the turning points and overcoming barriers reunification programs",
        "authors": ["Andreopoulos", "Wexler"],
        "year": "2022",
        "source": "web_scrape",
        "abstract": "Critique of rigid reunification programs, suggesting they may retraumatize children and mimic coercive dynamics.",
        "url": "https://scholar.google.com/scholar?q=The+solution+to+parental+alienation+critique+Andreopoulos+2022"
    },
    {
        "title": "Review of Intensive Reunification Therapies",
        "authors": ["Multiple Authors"],
        "year": "2022",
        "source": "web_scrape",
        "abstract": "Examination of six intensive reunification therapy programs (e.g., Family Bridges), concluding many tenets are questionable and evidence is weak.",
        "url": "https://scholar.google.com/scholar?q=Review+of+Intensive+Reunification+Therapies+2022"
    },
    
    # Recent Research 2024-2025
    {
        "title": "Parental Alienation and Reunification Therapy: An Evidence-Based Review",
        "authors": ["Ghia Townsend"],
        "year": "2025",
        "source": "web_scrape",
        "abstract": "Evidence-based review discussing reunification therapy as a clinical approach for parental alienation with ethical, child-centered principles.",
        "url": "https://scholar.google.com/scholar?q=Ghia+Townsend+Parental+Alienation+and+Reunification+Therapy+2025"
    },
    {
        "title": "Evaluating Reunification Therapy from the Child's Perspective: Family Reunification and Restoration Program (FRRP)",
        "authors": ["Joshua Marsden", "Hesam Varavei"],
        "year": "2025",
        "source": "web_scrape",
        "abstract": "Examines experiences of children and adolescents in court-mandated FRRP, noting perceived safety and support.",
        "url": "https://scholar.google.com/scholar?q=Evaluating+Reunification+Therapy+from+the+Child+Perspective+Marsden+2025"
    },
    {
        "title": "Implementing Limits to Reunification Therapy: Is There a Way Forward for Canada?",
        "authors": ["Scott", "Jaffe", "Heslop", "Reurink"],
        "year": "2024",
        "source": "web_scrape",
        "abstract": "Raises concerns about reunification therapy in situations of family violence and when conducted without thorough assessment.",
        "url": "https://scholar.google.com/scholar?q=Implementing+Limits+to+Reunification+Therapy+Scott+Jaffe+2024"
    },
    {
        "title": "Challenging the Consistency of Reunification Therapy in California Family Law",
        "authors": ["California Law Review"],
        "year": "2024",
        "source": "web_scrape",
        "abstract": "Addresses concerns regarding uniformity, effectiveness, and adherence to best practices of reunification therapy in California legal framework.",
        "url": "https://scholar.google.com/scholar?q=Challenging+the+Consistency+of+Reunification+Therapy+in+California+2024"
    },
    {
        "title": "Reunification therapy versus family integration therapy: A problem of taxonomy",
        "authors": ["Terry Singh", "Joel Mader"],
        "year": "2025",
        "source": "web_scrape",
        "abstract": "Presents an integrative framework for addressing parent-child contact issues, distinguishing between reunification and integration therapy.",
        "url": "https://scholar.google.com/scholar?q=Reunification+therapy+versus+family+integration+therapy+Singh+2025"
    }
]

def ingest_papers():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    count = 0
    for paper in PAPERS_TO_INGEST:
        try:
            # Generate pseudo ID
            pseudo_id = f"rt_gen_{hashlib.md5(paper['title'].encode()).hexdigest()[:10]}"
            
            # Check dupes
            cur.execute("SELECT id FROM papers WHERE title = %s", (paper['title'],))
            if cur.fetchone():
                print(f"Skipping duplicate: {paper['title'][:20]}...")
                continue
                
            cur.execute("""
                INSERT INTO papers (
                    title, authors, source, source_url,
                    ssrn_id, published_date,
                    abstract, quality_score, created_at, keywords
                ) VALUES (
                    %s, %s, %s, %s,
                    %s, %s,
                    %s, %s, NOW(), %s
                )
            """, (
                paper['title'],
                paper['authors'],
                'web_scrape',
                paper['url'],
                pseudo_id,
                f"{paper['year']}-01-01",
                paper['abstract'],
                5.0,
                ["Reunification Therapy", "Parental Alienation"]
            ))
            print(f"Ingested: {paper['title'][:40]}...")
            count += 1
        except psycopg2.errors.CheckViolation as e:
            print(f"[INGEST] Constraint Violation: {paper['title'][:30]}... Source 'web_scrape' invalid.")
            conn.rollback()
            continue
        except Exception as e:
            print(f"[INGEST] Error inserting {paper['title'][:20]}: {e}")
            conn.rollback()
            continue
            
    conn.commit()
    print(f"Successfully ingested {count} papers.")
    cur.close()
    conn.close()

if __name__ == "__main__":
    ingest_papers()
