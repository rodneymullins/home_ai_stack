#!/usr/bin/env python3
"""
Scrape Reddit r/Slots for community insights on machines
Requires: pip install praw
"""
import praw
import psycopg2
from datetime import datetime
import re

# Reddit API credentials (user needs to create these at https://www.reddit.com/prefs/apps)
REDDIT_CLIENT_ID = "YOUR_CLIENT_ID"
REDDIT_CLIENT_SECRET = "YOUR_CLIENT_SECRET"
REDDIT_USER_AGENT = "casino-analytics-bot/1.0"

def analyze_sentiment(text):
    """Simple keyword-based sentiment analysis"""
    text_lower = text.lower()
    
    # Positive indicators
    positive_keywords = ['hit big', 'won', 'jackpot', 'love', 'hot', 'loose', 'win', 'paid out', 'bonus']
    positive_score = sum(1 for word in positive_keywords if word in text_lower)
    
    # Negative indicators  
    negative_keywords = ['cold', 'tight', 'waste', 'avoid', 'lost', 'never hit', 'scam', 'rigged']
    negative_score = sum(1 for word in negative_keywords if word in text_lower)
    
    if positive_score > negative_score + 1:
        return 'positive'
    elif negative_score > positive_score + 1:
        return 'negative'
    else:
        return 'neutral'

def scrape_reddit_for_machine(reddit, machine_name, limit=10):
    """Search r/Slots for mentions of a specific machine"""
    print(f"\n🔍 Searching Reddit for: {machine_name}")
    
    subreddit = reddit.subreddit('Slots')
    search_term = machine_name.replace('(PROG)', '').replace('(MD)', '').strip()
    
    feedback_items = []
    
    try:
        for submission in subreddit.search(f'"{search_term}"', limit=limit):
            # Analyze submission title + body
            full_text = f"{submission.title} {submission.selftext}"
            sentiment = analyze_sentiment(full_text)
            
            # Extract excerpt (first 200 chars of relevant text)
            excerpt = full_text[:200].strip()
            
            feedback_items.append({
                'machine_name': machine_name.upper(),
                'source': 'reddit',
                'sentiment': sentiment,
                'excerpt': excerpt,
                'author': str(submission.author),
                'posted_date': datetime.fromtimestamp(submission.created_utc),
                'url': f"https://reddit.com{submission.permalink}"
            })
            
            print(f"  ✓ Found: '{submission.title}' ({sentiment})")
        
        return feedback_items
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return []

def save_feedback_to_db(feedback_items):
    """Save feedback to database"""
    if not feedback_items:
        return 0
    
    try:
        conn = psycopg2.connect(database="postgres", user="rod")
        cur = conn.cursor()
        
        inserted = 0
        for item in feedback_items:
            cur.execute("""
                INSERT INTO community_feedback 
                (machine_name, source, sentiment, excerpt, author, posted_date, url)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                item['machine_name'],
                item['source'],
                item['sentiment'],
                item['excerpt'],
                item['author'],
                item['posted_date'],
                item['url']
            ))
            inserted += 1
        
        conn.commit()
        cur.close()
        conn.close()
        return inserted
        
    except Exception as e:
        print(f"  DB Error: {e}")
        return 0

def main():
    """Scrape Reddit feedback for top machines"""
    
    # Check if credentials are configured
    if REDDIT_CLIENT_ID == "YOUR_CLIENT_ID":
        print("⚠️  Reddit API credentials not configured!")
        print("Please create an app at: https://www.reddit.com/prefs/apps")
        print("Then update REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET in this script.\n")
        return
    
    # Initialize Reddit client
    reddit = praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT
    )
    
    # Get popular machines from database
    conn = psycopg2.connect(database="postgres", user="rod")
    cur = conn.cursor()
    
    cur.execute("""
        SELECT DISTINCT m.machine_name, COUNT(j.id) as hit_count
        FROM slot_machines m
        LEFT JOIN jackpots j ON m.machine_name = j.machine_name
        GROUP BY m.machine_name
        HAVING COUNT(j.id) > 20
        ORDER BY COUNT(j.id) DESC
        LIMIT 10
    """)
    
    machines = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    
    print(f"🎰 Scraping Reddit insights for {len(machines)} popular machines...\n")
    
    total_feedback = 0
    for machine in machines:
        feedback = scrape_reddit_for_machine(reddit, machine, limit=5)
        saved = save_feedback_to_db(feedback)
        total_feedback += saved
    
    print(f"\n✅ Scraped {total_feedback} Reddit posts/comments")

if __name__ == "__main__":
    main()
