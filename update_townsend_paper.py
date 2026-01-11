import psycopg2

DB_CONFIG = {'database': 'research_papers', 'user': 'rod', 'host': '192.168.1.211'}

def update_townsend_paper():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    # Direct content scraped from the URL
    new_url = "https://torontopsychologicalservices.com/parental-alienation-and-reunification-therapy-an-evidence-based-review/"
    new_abstract = """
    A balanced, evidence-based review of Parental Alienation and Reunification Therapy by Ghia Townsend.
    
    The model proposed at Toronto Psychological Services and Research Centre (TPSRC) reflects the complexities and responsibilities inherent in working with families affected by parental alienation. The approach is grounded in trauma-informed principles and clinical best practices, structured around four interrelated phases: Assessment and Preparation, Psychoeducation, Facilitated Reconnection, and Maintenance and Monitoring.
    
    Phase One: Thorough assessment of family system (individual interviews, consultation, doc review) to distinguish between alienation, estrangement, and complex hybrid cases.
    Phase Two: Psychoeducation for parents and child on co-parenting, loyalty conflicts, and safety.
    Phase Three: Facilitated reconnection with structured contact, progressing to deeper work as child shows readiness.
    Phase Four: Ongoing maintenance and monitoring.
    
    Distinguishes the model by respect for emotional realities of all involved and commitment to ethical neutrality.
    """
    
    try:
        cur.execute("""
            UPDATE papers 
            SET source_url = %s, abstract = %s, source = 'web_scrape'
            WHERE title ILIKE '%Parental Alienation and Reunification Therapy: An Evidence-Based Review%'
        """, (new_url, new_abstract))
        
        if cur.rowcount > 0:
            print("Successfully updated Ghia Townsend paper.")
        else:
            print("Could not find Ghia Townsend paper to update.")
            
        conn.commit()
    except Exception as e:
        print(f"Error updating paper: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    update_townsend_paper()
