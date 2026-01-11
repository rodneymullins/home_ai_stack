import requests
from bs4 import BeautifulSoup
import os
import hashlib
import re
import psycopg2
from urllib.parse import unquote

DB_CONFIG = {'database': 'research_papers', 'user': 'rod', 'host': '192.168.1.211'}
DOWNLOAD_DIR = "/Users/rod/Antigravity/home_ai_stack/papers_pdf/child_rights_ngo"

def setup_dirs():
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)

def get_pdf_links():
    url = "https://childrightsngo.com/download/"
    print(f"Fetching {url}...")
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        links = []
        
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.lower().endswith('.pdf'):
                text = a.get_text(strip=True)
                links.append((text, href))
                
        print(f"Found {len(links)} PDF links.")
        return links
    except Exception as e:
        print(f"Error scraping: {e}")
        return []

def download_file(url, title):
    try:
        # Clean filename
        filename = unquote(url.split('/')[-1])
        # fallback if filename is empty or weird
        if not filename or filename.startswith('?'):
            filename = f"{hashlib.md5(url.encode()).hexdigest()}.pdf"
            
        filepath = os.path.join(DOWNLOAD_DIR, filename)
        
        if os.path.exists(filepath):
            print(f"File exists: {filename}")
            return filepath
            
        print(f"Downloading {filename}...")
        resp = requests.get(url, stream=True)
        resp.raise_for_status()
        
        with open(filepath, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
                
        return filepath
    except Exception as e:
        print(f"Failed to download {url}: {e}")
        return None

def ingest_paper(title, url, filepath):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Parse metadata from filename/title
        # Filenames often have format "Author - Title IMP.pdf" or "Title Dr Author.pdf"
        filename = os.path.basename(filepath)
        clean_name = filename.replace('.pdf', '').replace('%20', ' ')
        
        authors = ["Child Rights NGO"]
        # Basic heuristic for authors
        if "Dr." in clean_name or "Dr " in clean_name:
            # Extract name after Dr.
            pass # Keep it simple for now
            
        # Create pseudo-ID
        pseudo_id = f"crn_dl_{hashlib.md5(url.encode()).hexdigest()[:10]}"
        
        # Check if exists
        cur.execute("SELECT id FROM papers WHERE source_url = %s", (url,))
        if cur.fetchone():
            print(f"Updating PDF path for {title[:20]}...")
            cur.execute("""
                UPDATE papers 
                SET pdf_path = %s, pdf_url = %s 
                WHERE source_url = %s
            """, (filepath, url, url))
        else:
            print(f"Inserting new paper: {title[:30]}...")
            cur.execute("""
                INSERT INTO papers (
                    title, authors, source, source_url, 
                    pdf_url, pdf_path, ssrn_id, 
                    published_date, abstract, quality_score, created_at
                ) VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, NOW()
                )
            """, (
                clean_name, # Use filename as title if link text is bad
                ["Child Rights NGO"], # Default
                'child_rights_ngo',
                url,
                url,
                filepath,
                pseudo_id,
                '2026-01-01',
                f"Downloaded from ChildRightsNGO.com. Original text: {title}",
                5.0
            ))
            
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"DB Error: {e}")

def main():
    setup_dirs()
    links = get_pdf_links()
    
    for text, url in links:
        # Fix relative URLs if any
        if not url.startswith('http'):
            if url.startswith('/'):
                url = f"https://childrightsngo.com{url}"
            else:
                url = f"https://childrightsngo.com/download/{url}"
                
        filepath = download_file(url, text)
        if filepath:
            ingest_paper(text, url, filepath)

if __name__ == "__main__":
    main()
