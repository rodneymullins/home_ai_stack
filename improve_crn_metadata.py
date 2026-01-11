import psycopg2
import re

DB_CONFIG = {'database': 'research_papers', 'user': 'rod', 'host': '192.168.1.211'}

def improve_metadata():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    # Fetch all papers from this source
    cur.execute("SELECT id, title FROM papers WHERE source = 'child_rights_ngo'")
    papers = cur.fetchall()
    
    updated = 0
    for pid, title in papers:
        # Regex to find Dr. Name
        # Looking for "Dr. [First] [Last]" or "Dr.[First].[Last]"
        match = re.search(r'Dr\.?\s*([A-Za-z]+(?:\s|\.)+[A-Za-z]+)', title)
        if match:
            author_name = match.group(1).replace('.', ' ').strip()
            # Add "Dr." back for dignity? Or just name. Let's just use name for array.
            full_author = f"Dr. {author_name}"
            
            print(f"Update {pid}: {title[:30]} -> Author: {full_author}")
            
            cur.execute("""
                UPDATE papers 
                SET authors = ARRAY[%s] 
                WHERE id = %s
            """, (full_author, pid))
            updated += 1
            
    conn.commit()
    print(f"Updated authors for {updated} papers.")
    cur.close()
    conn.close()

if __name__ == "__main__":
    improve_metadata()
