from datetime import datetime, timedelta
import feedparser
from pytrends.request import TrendReq
from utils.db_pool import get_db_connection
from psycopg2.extras import RealDictCursor

# Simple in-memory cache for jackpots (replicating original logic)
jackpot_cache = []
jackpot_cache_time = None

def get_jackpots():
    global jackpot_cache, jackpot_cache_time
    if jackpot_cache and jackpot_cache_time:
        if (datetime.now() - jackpot_cache_time).seconds < 30:
            return jackpot_cache

    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("SELECT location_id, machine_name, denomination, scraped_at, amount, hit_timestamp FROM jackpots WHERE machine_name NOT ILIKE '%Poker%' AND machine_name NOT ILIKE '%Keno%' ORDER BY hit_timestamp DESC NULLS LAST, scraped_at DESC LIMIT 50")
            jackpots = cur.fetchall()
            cur.close()
            conn.close()
            jackpot_cache = [dict(jp) for jp in jackpots]
            jackpot_cache_time = datetime.now()
            return jackpot_cache
        except Exception as e:
            print(f"Error fetching jackpots: {e}")
    return [{'location_id': 'HD0104', 'machine_name': 'IGT MULTI-GAME', 'denomination': '$1.00', 'scraped_at': datetime.now()}]

def get_multi_casino_stats():
    """Get stats from multi_casino_jackpots table"""
    conn = get_db_connection()
    if not conn:
        return {}
        
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # 1. Latest Jackpots (Feed)
        try:
            cur.execute("""
                SELECT casino, machine_name, amount, date_text, source_url
                FROM multi_casino_jackpots
                ORDER BY id DESC
                LIMIT 50
            """)
            latest_jackpots = [dict(row) for row in cur.fetchall()]
        except:
            latest_jackpots = []

        # 2. Casino Leaderboard
        try:
            cur.execute("""
                SELECT casino, COUNT(*) as hits, AVG(amount) as avg_payout, MAX(amount) as max_payout
                FROM multi_casino_jackpots
                GROUP BY casino
                ORDER BY COUNT(*) DESC
            """)
            casinos = [dict(row) for row in cur.fetchall()]
        except:
            casinos = []
            
        # 3. Top Machines Aggregated
        try:
            cur.execute("""
                SELECT machine_name, COUNT(*) as hits, AVG(amount) as avg_payout, MAX(amount) as max_payout,
                       STRING_AGG(DISTINCT casino, ', ') as locations
                FROM multi_casino_jackpots
                GROUP BY machine_name
                HAVING COUNT(*) >= 2
                ORDER BY hits DESC, avg_payout DESC
                LIMIT 10
            """)
            top_machines = [dict(row) for row in cur.fetchall()]
        except:
            top_machines = []
        
        cur.close()
        conn.close()
        
        return {
            'latest': latest_jackpots,
            'casinos': casinos,
            'top_machines': top_machines
        }
    except Exception as e:
        print(f"Error getting multi-casino stats: {e}")
        return {}

def get_trending_searches(geo='US'):
    # Region-specific demo data
    if geo == 'united_states':
        demo_data = [
            {'title': 'NFL Playoffs 2025', 'traffic': 'HOT'},
            {'title': 'Super Bowl Halftime Show', 'traffic': 'HOT'},
            {'title': 'New iPhone Release', 'traffic': 'HOT'},
            {'title': 'Tax Season 2025', 'traffic': 'HOT'},
            {'title': 'March Madness Bracket', 'traffic': 'HOT'}
        ]
    else:  # Global
        demo_data = [
            {'title': 'FIFA World Cup Qualifiers', 'traffic': 'HOT'},
            {'title': 'Climate Summit 2025', 'traffic': 'HOT'},
            {'title': 'SpaceX Mars Mission', 'traffic': 'HOT'},
            {'title': 'Olympics 2025', 'traffic': 'HOT'},
            {'title': 'Nobel Prize Winners', 'traffic': 'HOT'}
        ]
    
    try:
        pytrends = TrendReq(hl='en-US', tz=360, timeout=(10, 25), retries=2)
        trending = pytrends.trending_searches(pn=geo)
        result = [{'title': item, 'traffic': 'HOT'} for item in trending[0].head(5).tolist()]
        return result if result else demo_data
    except Exception as e:
        print(f"Using demo data for {geo}: {e}")
        return demo_data

def get_news():
    try:
        feeds = [('https://www.cnbc.com/id/100003114/device/rss/rss.html', 'CNBC'), ('https://feeds.reuters.com/reuters/businessNews', 'Reuters')]
        news = []
        for feed_url, source in feeds:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:5]:
                    news.append({'title': entry.title, 'link': entry.link, 'source': source, 'published': entry.get('published', 'Recently')[:16]})
            except:
                pass
        return news[:10] if news else [{'title': 'Markets Rally on Strong Economic Data', 'link': '#', 'source': 'Demo News', 'published': 'Today'}]
    except Exception as e:
        print(f"Error fetching news: {e}")
        return [{'title': 'Markets Rally on Strong Economic Data', 'link': '#', 'source': 'Demo News', 'published': 'Today'}]

def get_services():
    return [
        {'name': 'Homer', 'icon': '🏠', 'url': 'http://192.168.1.176'},
        {'name': 'Jellyfin', 'icon': '🎬', 'url': 'http://192.168.1.176:8096'},
        {'name': 'Nextcloud', 'icon': '☁️', 'url': 'http://192.168.1.176:8083'},
        {'name': 'Jellyseerr', 'icon': '📺', 'url': 'http://192.168.1.176:5055'},
        {'name': 'Sonarr', 'icon': '📡', 'url': 'http://192.168.1.176:8989'},
        {'name': 'Radarr', 'icon': '🎥', 'url': 'http://192.168.1.176:7878'}
    ]

def format_time_ago(dt):
    if not dt: return ""
    if isinstance(dt, str): return dt # Handle string timestamps if any
    now = datetime.now()
    diff = now - dt
    if diff.days > 0: return f"{diff.days}d ago"
    hours = diff.seconds // 3600
    if hours > 0: return f"{hours}h ago"
    minutes = (diff.seconds % 3600) // 60
    return f"{minutes}m ago"
