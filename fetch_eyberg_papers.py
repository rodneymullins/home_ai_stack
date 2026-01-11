import requests
import time
import json
import os

def fetch_eyberg_papers():
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    
    # 1. Search for IDs
    search_url = f"{base_url}esearch.fcgi"
    search_params = {
        "db": "pubmed",
        "term": "Eyberg SM[Author]",
        "retmax": "500",
        "retmode": "json"
    }
    
    print("Searching PubMed for papers by 'Eyberg SM'...")
    try:
        response = requests.get(search_url, params=search_params)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"Error searching PubMed: {e}")
        return
    
    id_list = data.get("esearchresult", {}).get("idlist", [])
    print(f"Found {len(id_list)} papers. Fetching details...")
    
    if not id_list:
        print("No papers found.")
        return

    # 2. Fetch Details in batches
    batch_size = 100
    all_papers = []
    
    fetch_url = f"{base_url}esummary.fcgi"
    
    for i in range(0, len(id_list), batch_size):
        batch_ids = id_list[i:i+batch_size]
        ids_str = ",".join(batch_ids)
        
        fetch_params = {
            "db": "pubmed",
            "id": ids_str,
            "retmode": "json"
        }
        
        try:
            resp = requests.get(fetch_url, params=fetch_params)
            resp.raise_for_status()
            batch_data = resp.json()
            
            # Parse result
            result = batch_data.get("result", {})
            # 'result' contains uids as keys, plus 'uids' list (which we can iterate over or just use the keys)
            
            for uid in batch_ids:
                if uid in result:
                    paper = result[uid]
                    all_papers.append(paper)
                    
            print(f"Fetched {len(all_papers)}/{len(id_list)}...")
            
        except Exception as e:
            print(f"Error fetching batch {i}: {e}")
        
        time.sleep(0.3) # Be nice to API
        
    # 3. Save to Markdown
    output_file = "eyberg_papers.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("# Publications by Sheila M. Eyberg\n\n")
        f.write(f"**Total Found:** {len(all_papers)}\n")
        f.write(f"**Source:** PubMed (NCBI)\n")
        f.write(f"**Date Fetched:** {time.strftime('%Y-%m-%d')}\n\n")
        f.write("---\n\n")
        
        # Sort by date (descending)
        # PubMed dates can be tricky ("1998 Jun"), we'll do best effort sort
        def get_sort_key(p):
            return p.get("pubdate", "")
            
        all_papers.sort(key=get_sort_key, reverse=True)
        
        for paper in all_papers:
            title = paper.get("title", "No Title")
            authors_list = paper.get("authors", [])
            authors = [a.get("name", "") for a in authors_list]
            author_str = ", ".join(authors)
            source = paper.get("source", "")
            pubdate = paper.get("pubdate", "")
            
            # Construct link
            pmid = paper.get("uid", "")
            link = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            
            f.write(f"### [{title}]({link})\n")
            f.write(f"- **Authors:** {author_str}\n")
            f.write(f"- **Journal:** {source}\n")
            f.write(f"- **Date:** {pubdate}\n")
            f.write("\n")

    print(f"Successfully saved {len(all_papers)} papers to {os.path.abspath(output_file)}")

if __name__ == "__main__":
    fetch_eyberg_papers()
