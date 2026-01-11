import psycopg2

DB_CONFIG = {'database': 'research_papers', 'user': 'rod', 'host': '192.168.1.211'}

def update_constraint():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    try:
        # 1. Drop old constraint
        cur.execute("ALTER TABLE papers DROP CONSTRAINT papers_source_check;")
        
        # 2. Add new constraint with 'book_reference'
        cur.execute("""
            ALTER TABLE papers 
            ADD CONSTRAINT papers_source_check 
            CHECK (source IN (
                'arxiv', 'biorxiv', 'medrxiv', 'psyarxiv', 
                'pubmed', 'nber', 'ssrn', 
                'child_rights_ngo', 'psychology_today', 'web_scrape', 
                'book_reference', 'other'
            ));
        """)
        
        conn.commit()
        print("Successfully updated constraint to include 'book_reference'.")
        
    except Exception as e:
        print(f"Error updating schema: {e}")
        conn.rollback()
    
    conn.close()

if __name__ == "__main__":
    update_constraint()
