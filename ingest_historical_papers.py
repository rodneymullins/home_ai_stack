import psycopg2
import hashlib

from config import DB_CONFIG

PAPERS_TO_INGEST = [
    # PA Papers (2000-2023)
    {
        "title": "Patterns of Parental Alienation Syndrome: A Qualitative Study of Adults Who were Alienated from a Parent as a Child",
        "authors": ["Amy J. L. Baker"],
        "year": "2006",
        "source": "web_scrape",
        "abstract": "Foundational qualitative study identifying patterns of alienation strategies and their impact on adults.",
        "url": "https://scholar.google.com/scholar?q=Baker+Patterns+of+Parental+Alienation+Syndrome+2006"
    },
    {
        "title": "Parental Alienation: Strategies and Tactics",
        "authors": ["Jennifer J. Harman", "Matthewson"],
        "year": "2020",
        "source": "web_scrape",
        "abstract": "Comprehensive analysis of specific strategies used by alienating parents, contributing to the behavioral breakdown of PA.",
        "url": "https://scholar.google.com/scholar?q=Harman+Parental+Alienation+Strategies+and+Tactics+2020"
    },
    {
        "title": "Developmental psychology and the scientific status of parental alienation",
        "authors": ["Richard A. Warshak"],
        "year": "2020",
        "source": "web_scrape",
        "abstract": "Examining PA through the lens of developmental psychology to validate its scientific status.",
        "url": "https://scholar.google.com/scholar?q=Warshak+Developmental+psychology+and+the+scientific+status+of+parental+alienation"
    },
     {
        "title": "Parental Alienation as Family Violence",
        "authors": ["Jennifer J. Harman", "Kruk", "Hines"],
        "year": "2018",
        "source": "web_scrape",
        "abstract": "Argues that parental alienation meets the criteria for family violence and child abuse.",
        "url": "https://scholar.google.com/scholar?q=Harman+Parental+Alienation+as+Family+Violence+2018"
    },
    
    # RT Papers (2000-2023)
     {
        "title": "Family Bridges: Using insights from social science to reconnect parents and alienated children",
        "authors": ["Richard A. Warshak"],
        "year": "2010",
        "source": "web_scrape",
        "abstract": "Seminal paper describing the Family Bridges program, a workshop-based intervention for severe alienation.",
        "url": "https://scholar.google.com/scholar?q=Warshak+Family+Bridges+2010"
    },
    {
        "title": "Reunification Planning and Therapy: A Treatment Model",
        "authors": ["S. Richard Sauber"],
        "year": "2013",
        "source": "web_scrape",
        "abstract": "Conceptualizes reunification as addressing disruption in a previously intact family system.",
        "url": "https://scholar.google.com/scholar?q=Sauber+Reunification+Planning+and+Therapy+2013"
    },
    {
        "title": "Recommendations for best practice in response to parental alienation",
        "authors": ["Templer", "Matthewson", "Haines"],
        "year": "2017",
        "source": "web_scrape",
        "abstract": "Systematic review providing evidence-based recommendations for clinical practice in PA cases.",
        "url": "https://scholar.google.com/scholar?q=Templer+Recommendations+for+best+practice+parental+alienation+2017"
    },
    {
        "title": "Clinical tasks with alienated children",
        "authors": ["Baker", "Sauber"],
        "year": "2013",
        "source": "web_scrape",
        "abstract": "Outlines specific clinical tasks and therapeutic goals for working with alienated children.",
        "url": "https://scholar.google.com/scholar?q=Baker+Sauber+Clinical+tasks+with+alienated+children+2013"
    },
    {
        "title": "Ten parental alienation fallacies that compromise decisions in court and in therapy",
        "authors": ["Richard A. Warshak"],
        "year": "2015",
        "source": "web_scrape",
        "abstract": "Identifies common fallacies about PA that lead to poor legal and clinical decisions.",
        "url": "https://scholar.google.com/scholar?q=Warshak+Ten+parental+alienation+fallacies+2015"
    },
    {
        "title": "Denial of Ambivalence as a Hallmark of Parental Alienation",
        "authors": ["Jaffe", "Thakkar", "Piron"],
        "year": "2017",
        "source": "web_scrape",
        "abstract": "Discusses the lack of ambivalence (all-good vs all-bad splitting) in alienated children's views of parents.",
        "url": "https://scholar.google.com/scholar?q=Jaffe+Denial+of+Ambivalence+parental+alienation+2017"
    }
]

def ingest_papers():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    count = 0
    for paper in PAPERS_TO_INGEST:
        try:
            # Generate pseudo ID
            pseudo_id = f"hist_{hashlib.md5(paper['title'].encode()).hexdigest()[:10]}"
            
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
                5.0, # Baseline score
                ["Historical Research", "Parental Alienation", "Reunification"]
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
    print(f"Successfully ingested {count} historical papers.")
    cur.close()
    conn.close()

if __name__ == "__main__":
    ingest_papers()
