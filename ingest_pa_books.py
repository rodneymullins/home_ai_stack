import psycopg2
import hashlib

from config import DB_CONFIG

BOOKS_TO_INGEST = [
    # Seminal / General PA Books
    {
        "title": "Parental Alienation: Science and Law",
        "authors": ["William Bernet", "Demosthenes Lorandos"],
        "year": "2020",
        "abstract": "Comprehensive encyclopedia on parental alienation with contributions from many experts. Covers legal and scientific aspects.",
        "url": "https://www.ccthomas.com/details.cfm?P_ISBN13=9780398093242"
    },
    {
        "title": "Divorce Poison: How to Protect Your Family from Bad-mouthing and Brainwashing",
        "authors": ["Richard A. Warshak"],
        "year": "2010",
        "abstract": "Widely read guide for alienated parents, offering specific strategies for dealing with badmouthing and brainwashing tactics.",
        "url": "https://warshak.com/divorce-poison/"
    },
    {
        "title": "Adult Children of Parental Alienation Syndrome: Breaking the Ties That Bind",
        "authors": ["Amy J. L. Baker"],
        "year": "2007",
        "abstract": " Insight into the experiences of adult children who underwent parental alienation, helping parents understand their children's perspectives.",
        "url": "https://www.amyjlbaker.com/books.html"
    },
    {
        "title": "Co-Parenting With A Toxic Ex: What To Do When Your Ex-Spouse Tries To Turn the Kids Against You",
        "authors": ["Amy J. L. Baker", "Paul R. Fine"],
        "year": "2014",
        "abstract": "Practical guide specifically for alienated parents from a developmental scientist perspective.",
        "url": "https://www.amyjlbaker.com/books.html"
    },
    {
        "title": "Understanding Parental Alienation: Learning to Cope, Helping to Heal",
        "authors": ["Karen Woodall", "Nick Woodall"],
        "year": "2017",
        "abstract": "Balances theory and practical advice for alienated parents, drawing on clinical experience from the Family Separation Clinic.",
        "url": "https://www.karenwoodall.blog"
    },
    
    # Reunification Focused Books
    {
        "title": "Beyond Divorce Casualties: Reunifying the Alienated Family",
        "authors": ["Douglas Darnall"],
        "year": "2010",
        "abstract": "Detailed guide on reunification therapy, covering preparation, legal aspects, and assessing reunifiability.",
        "url": "https://www.amazon.com/Beyond-Divorce-Casualties-Reunifying-Alienated/dp/1589794562"
    },
    {
        "title": "Reunification Family Therapy: A Treatment Manual",
        "authors": ["Jan Faust"],
        "year": "2018",
        "abstract": "Evidence-based manual for clinicians outlining a structured approach to repairing parent-child relationships.",
        "url": "https://www.hogrefe.com/us/shop/reunification-family-therapy-85579.html"
    },
    {
        "title": "Restoring Family Connections: Helping Targeted Parents and Adult Alienated Children",
        "authors": ["Amy J. L. Baker", "Paul R. Fine", "Alianna LaCheen-Baker"],
        "year": "2020",
        "abstract": "Guide for therapists dealing with broken family relationships due to parental alienation.",
        "url": "https://www.amyjlbaker.com/books.html"
    },
    {
        "title": "Overcoming the Co-Parenting Trap: Essential Parenting Skills When a Child Resists a Parent",
        "authors": ["John A. Moran", "Tyler Sullivan", "Matthew Sullivan"],
        "year": "2015",
        "abstract": "Focuses on high-conflict dynamics and children resisting contact.",
        "url": "https://overcomingbarriers.org/"
    },
    {
        "title": "Parenting the Alienated Child: Reconnecting with Lost Hearts",
        "authors": ["Loretta Maase"],
        "year": "2024",
        "abstract": "Evidence-based guidance for alienated parents offering practical interventions grounded in family systems and trauma-informed principles.",
        "url": "https://www.barnesandnoble.com/"
    }
]

def ingest_books():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    count = 0
    for book in BOOKS_TO_INGEST:
        try:
            # Generate pseudo ID
            pseudo_id = f"book_{hashlib.md5(book['title'].encode()).hexdigest()[:10]}"
            
            # Check dupes
            cur.execute("SELECT id FROM papers WHERE title = %s", (book['title'],))
            if cur.fetchone():
                print(f"Skipping duplicate: {book['title'][:20]}...")
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
                book['title'],
                book['authors'],
                'book_reference', # Distinguish from papers
                book['url'],
                pseudo_id,
                f"{book['year']}-01-01",
                book['abstract'],
                5.0,
                ["Book", "Parental Alienation", "Reunification"]
            ))
            print(f"Ingested Book: {book['title'][:40]}...")
            count += 1
        except psycopg2.errors.CheckViolation as e:
            print(f"[INGEST] Constraint Violation: {book['title'][:30]}... Source 'book_reference' invalid.")
            conn.rollback()
            continue
        except Exception as e:
            print(f"[INGEST] Error inserting {book['title'][:20]}: {e}")
            conn.rollback()
            continue
            
    conn.commit()
    print(f"Successfully ingested {count} books.")
    cur.close()
    conn.close()

if __name__ == "__main__":
    ingest_books()
