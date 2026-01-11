import psycopg2
import re
from config import DB_CONFIG

# Allowed sources from AGENTS.md (Single Source of Truth)
ALLOWED_SOURCES = {
    'arxiv', 'biorxiv', 'medrxiv', 'psyarxiv', 'pubmed', 'nber', 'ssrn', 
    'child_rights_ngo', 'psychology_today', 'web_scrape', 'book_reference', 'other'
}

def normalize_title(title):
    """Normalize title for fuzzy duplicate detection."""
    if not title:
        return ""
    # Lowercase, remove non-alphanumeric, strip whitespace
    return re.sub(r'[^a-z0-9]', '', title.lower())

def verify_integrity():
    print("--- [VERIFY] Starting Database Integrity Check ---")
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Fetch all papers
        cur.execute("SELECT id, title, source, authors, abstract, source_url FROM papers")
        records = cur.fetchall()
        
        print(f"--- [VERIFY] Scanned {len(records)} records ---")
        
        # Analysis Containers
        title_map = {}
        duplicates = []
        invalid_sources = []
        metadata_issues = []
        
        for pid, title, source, authors, abstract, url in records:
            # 1. Duplicate Check
            norm_title = normalize_title(title)
            if norm_title in title_map:
                duplicates.append({
                    'original': title_map[norm_title],
                    'duplicate': {'id': pid, 'title': title}
                })
            else:
                title_map[norm_title] = {'id': pid, 'title': title}
            
            # 2. Source Check
            if source not in ALLOWED_SOURCES:
                invalid_sources.append({'id': pid, 'source': source, 'title': title})
                
            # 3. Metadata Health
            issues = []
            if not authors or (isinstance(authors, list) and len(authors) == 0):
                issues.append("Missing Authors")
            if not abstract or len(abstract) < 10:
                issues.append("Missing/Short Abstract")
            if not url:
                issues.append("Missing URL")
                
            if issues:
                metadata_issues.append({'id': pid, 'title': title, 'issues': issues})

        # --- Report ---
        
        print("\n--- [REPORT] Duplicate Titles ---")
        if duplicates:
            print(f"Found {len(duplicates)} potential duplicates:")
            for d in duplicates[:10]:
                print(f"  - Dup ID {d['duplicate']['id']}: {d['duplicate']['title'][:50]}...")
                print(f"    Matches ID {d['original']['id']}: {d['original']['title'][:50]}...")
            if len(duplicates) > 10:
                print(f"  ... and {len(duplicates) - 10} more.")
        else:
            print("✅ No duplicates found.")
            
        print("\n--- [REPORT] Invalid Sources ---")
        if invalid_sources:
            print(f"Found {len(invalid_sources)} invalid sources:")
            for i in invalid_sources:
                print(f"  - ID {i['id']} ({i['source']}): {i['title'][:50]}...")
        else:
            print("✅ All sources valid.")
            
        print("\n--- [REPORT] Metadata Health ---")
        if metadata_issues:
            print(f"Found {len(metadata_issues)} records with missing metadata:")
            for m in metadata_issues[:10]:
                print(f"  - ID {m['id']}: {m['issues']} -> {m['title'][:50]}...")
            if len(metadata_issues) > 10:
                print(f"  ... and {len(metadata_issues) - 10} more.")
        else:
            print("✅ Metadata looks healthy.")

        cur.close()
        conn.close()
        print("\n--- [VERIFY] Check Complete ---")
        
    except Exception as e:
        print(f"❌ [VERIFY] Fatal Error: {e}")

if __name__ == "__main__":
    verify_integrity()
