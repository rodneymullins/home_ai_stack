import psycopg2
import hashlib

DB_CONFIG = {'database': 'research_papers', 'user': 'rod', 'host': '192.168.1.211'}

# Data from WorldCat Browser Subagent
BOOKS_TO_INGEST = [
    {
        "Title": "Parental alienation theory: official synopsis",
        "Author": "Parental Alienation Study Group (Organization) (Editor)",
        "Year": 2025,
        "ISBN": "9780398094744"
    },
    {
        "Title": "Challenging parental alienation: new directions for professionals and parents",
        "Author": "Jean Mercer, Margaret Drew",
        "Year": 2022,
        "ISBN": "9780367559762"
    },
    {
        "Title": "Parental alienation: an evidence-based approach",
        "Author": "Denise McCartan",
        "Year": 2022,
        "ISBN": "9780367741136"
    },
    {
        "Title": "Litigating parental alienation: evaluating and presenting an effective case in court",
        "Author": "Ashish Joshi (Editor)",
        "Year": 2021,
        "ISBN": "9781641058285"
    },
    {
        "Title": "The parental alienation syndrome: a family therapy and collaborative systems approach to amelioration",
        "Author": "Linda J. Gottlieb",
        "Year": 2012,
        "ISBN": "9780398087364"
    },
    {
        "Title": "Parent-Child Reunification: A Guide to Legal and Forensic Strategies",
        "Author": "Stanley S. Clawar",
        "Year": 2025,
        "ISBN": "9781641056052"
    },
    {
        "Title": "Reunification family therapy: a treatment manual",
        "Author": "Jan Faust",
        "Year": 2018,
        "ISBN": "9781138848146"
    },
    {
        "Title": "Working with alienated children and families: a clinical guidebook",
        "Author": "Amy J. L. Baker, S. Richard Sauber",
        "Year": 2013,
        "ISBN": "9780415518030"
    },
    {
        "Title": "Parental alienation: the handbook for mental health and legal professionals",
        "Author": "Demosthenes Lorandos, William Bernet, S. Richard Sauber (Editors)",
        "Year": 2013,
        "ISBN": "9780398087494"
    },
    {
        "Title": "Clinical tasks with alienated children and their families: practitioners' perspectives",
        "Author": "Amy J. L. Baker, S. Richard Sauber",
        "Year": 2013,
        "ISBN": "9780415518023"
    }
]

def ingest_books():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    count = 0
    for book in BOOKS_TO_INGEST:
        try:
            # Generate pseudo ID
            pseudo_id = f"wc_{hashlib.md5(book['Title'].encode()).hexdigest()[:10]}"
            
            # Check dupes
            cur.execute("SELECT id FROM papers WHERE title = %s", (book['Title'],))
            if cur.fetchone():
                print(f"Skipping duplicate: {book['Title'][:20]}...")
                continue
            
            # Authors to list
            authors = [a.strip() for a in book['Author'].split(',')]
            
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
                book['Title'],
                authors,
                'book_reference', 
                f"https://search.worldcat.org/search?q={book['ISBN']}", # Pseudo URL
                pseudo_id,
                f"{book['Year']}-01-01",
                f"WorldCat Result. ISBN: {book['ISBN']}",
                5.0,
                ["Book", "WorldCat", "Parental Alienation"]
            ))
            print(f"Ingested Book: {book['Title'][:40]}...")
            count += 1
        except Exception as e:
            print(f"Error inserting {book['Title'][:20]}: {e}")
            conn.rollback()
            continue
            
    conn.commit()
    print(f"Successfully ingested {count} WorldCat books.")
    cur.close()
    conn.close()

if __name__ == "__main__":
    ingest_books()
