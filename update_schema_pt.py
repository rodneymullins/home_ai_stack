import psycopg2

DB_CONFIG = {'database': 'research_papers', 'user': 'rod', 'host': '192.168.1.211'}

def update_schema():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        print("Dropping old constraint...")
        cur.execute("ALTER TABLE papers DROP CONSTRAINT papers_source_check;")
        
        print("Adding new constraint with expanded source list...")
        # Add psychology_today to the list
        cur.execute("""
            ALTER TABLE papers ADD CONSTRAINT papers_source_check 
            CHECK (source IN ('arxiv', 'psyarxiv', 'ssrn', 'nber', 'pubmed', 'semantic', 'biorxiv', 'child_rights_ngo', 'psychology_today', 'web_scrape', 'other'));
        """)
        
        conn.commit()
        print("Schema updated successfully.")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    update_schema()
