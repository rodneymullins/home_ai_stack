import psycopg2
import hashlib

from config import DB_CONFIG

PAPERS_TO_INGEST = [
    # Seminal Works
    {
        "title": "Parental Alienation Syndrome",
        "authors": ["Richard A. Gardner"],
        "year": "1985",
        "source": "seminal_work",
        "abstract": "The original work coining the term 'Parental Alienation Syndrome' (PAS), describing a disorder in which a child becomes obsessed with unjustified denigration of a parent during custody disputes.",
        "url": "https://scholar.google.com/scholar?q=Gardner+Parental+Alienation+Syndrome+1985"
    },
    {
        "title": "The Long-Term Effects of Parental Alienation on Adult Children: A Qualitative Research Study",
        "authors": ["Amy J. L. Baker"],
        "year": "2005",
        "source": "seminal_work",
        "abstract": "A qualitative study exploring the long-term effects of parental alienation on adult children, identifying patterns of alienation and lifelong impact.",
        "url": "https://scholar.google.com/scholar?q=Amy+Baker+Long+Term+Effects+Parental+Alienation+2005"
    },
    {
        "title": "Parental alienation: Toward the blossoming of a field of study",
        "authors": ["Jennifer J. Harman", "William Bernet", "et al."],
        "year": "2019",
        "source": "seminal_work",
        "abstract": "A comprehensive review of the literature emphasizing the consensus on alienating behaviors and framing parental alienation as a field of study.",
        "url": "https://doi.org/10.1007/s12144-019-00294-3"
    },
    
    # Recent Research 2024-2025
    {
        "title": "Understanding the Harmful Effects of Parental Alienation on Families",
        "authors": ["Scandinavian Journal of Public Health"],
        "year": "2024",
        "source": "web_scrape",
        "abstract": "Explores parental alienation as a valid construct and its impact on family dynamics, identifying eight distinct alienation strategies based on a survey of 1,212 participants.",
        "url": "https://scholar.google.com/scholar?q=Understanding+the+Harmful+Effects+of+Parental+Alienation+on+Families+2024"
    },
    {
        "title": "Effects Of Parental Alienation: A Phenomenological Study",
        "authors": ["Journal of Electrical Systems"],
        "year": "2024",
        "source": "web_scrape",
        "abstract": "Qualitative study utilizing interviews with alienated children to discover effects and coping mechanisms, revealing internal/external behavioral problems and complex trauma.",
        "url": "https://scholar.google.com/scholar?q=Effects+Of+Parental+Alienation+A+Phenomenological+Study+2024"
    },
    {
        "title": "'Parental alienation' allegations in the context of domestic violence: impacts on mother-child relationships",
        "authors": ["Taylor & Francis"],
        "year": "2024",
        "source": "web_scrape",
        "abstract": "Investigates impacts of alienation allegations on women and children, focusing on mother-child relationships in contexts of domestic violence.",
        "url": "https://scholar.google.com/scholar?q=Parental+alienation+allegations+in+the+context+of+domestic+violence+2024"
    },
    {
        "title": "Countering Arguments Against Parental Alienation as A Form of Family Violence and Child Abuse",
        "authors": ["Taylor & Francis Online"],
        "year": "2024",
        "source": "web_scrape",
        "abstract": "Refutes common arguments against classifying parental alienation as family violence using empirical evidence from over a hundred peer-reviewed studies.",
        "url": "https://scholar.google.com/scholar?q=Countering+Arguments+Against+Parental+Alienation+as+A+Form+of+Family+Violence+2024"
    },
    {
        "title": "The Scientific Rigor of Parental Alienation Studies: A Quality Assessment of the Peer-Reviewed Research",
        "authors": ["Springer Publishing"],
        "year": "2025",
        "source": "web_scrape",
        "abstract": "A comprehensive assessment of 156 studies, finding a consistent high level of scientific rigor in parental alienation research.",
        "url": "https://scholar.google.com/scholar?q=The+Scientific+Rigor+of+Parental+Alienation+Studies+2025"
    },
    {
        "title": "The Parental Alienation Field and the Future of Families",
        "authors": ["ResearchGate"],
        "year": "2025",
        "source": "web_scrape",
        "abstract": "Discusses controversies and proposes a reformulation focusing on the alienated child and systemic factors like marital conflict.",
        "url": "https://scholar.google.com/scholar?q=The+Parental+Alienation+Field+and+the+Future+of+Families+2025"
    },
    {
        "title": "The End of Gendered Policy: A New Public Policy Framework for Alienation in Families",
        "authors": ["ResearchGate"],
        "year": "2025",
        "source": "web_scrape",
        "abstract": "Examines 10 mistaken assumptions about parental alienation and proposes a new public policy framework for addressing alienation in families.",
        "url": "https://scholar.google.com/scholar?q=The+End+of+Gendered+Policy+Parental+Alienation+2025"
    },
    {
        "title": "Parental Alienation—What Do We Know, and What Do We (Urgently) Need to Know? A Narrative Review",
        "authors": ["ResearchGate"],
        "year": "2025",
        "source": "web_scrape",
        "abstract": "Narrative review exploring family breakdown, domestic violence, and alienation, highlighting experiences of fathers and impact on children.",
        "url": "https://scholar.google.com/scholar?q=Parental+Alienation+What+Do+We+Know+2025"
    }
]

def ingest_papers():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    count = 0
    for paper in PAPERS_TO_INGEST:
        try:
            # Create a pseudo source_check compatible source or use 'web_scrape'
            # We updated schema to allow 'web_scrape'
            
            # Generate pseudo ID
            pseudo_id = f"pa_gen_{hashlib.md5(paper['title'].encode()).hexdigest()[:10]}"
            
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
                ["Parental Alienation", "General Research"]
            ))
            print(f"Ingested: {paper['title'][:40]}...")
            count += 1
        except Exception as e:
            print(f"Error inserting {paper['title'][:20]}: {e}")
            conn.rollback()
            continue
            
    conn.commit()
    print(f"Successfully ingested {count} papers.")
    cur.close()
    conn.close()

if __name__ == "__main__":
    ingest_papers()
