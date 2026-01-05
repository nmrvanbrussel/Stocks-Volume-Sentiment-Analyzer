import requests
import time
import re
import yfinance as yf
from datetime import datetime, timezone
from pathlib import Path
import sys

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import REDDIT_CONFIG, DATABASE_PATH
from Database.db_utils import DatabaseManager

# Get credentials from config
CLIENT_ID = REDDIT_CONFIG['client_id']
CLIENT_SECRET = REDDIT_CONFIG['client_secret']
USER_AGENT = REDDIT_CONFIG['user_agent']
SUBREDDIT = REDDIT_CONFIG['subreddit']

# Validate credentials
if not CLIENT_ID or not CLIENT_SECRET:
    raise ValueError("Reddit credentials not found in config. Please create .env file with REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET")

def get_reddit_token():
    """Authenticate with Reddit API and return access token."""
    auth = requests.auth.HTTPBasicAuth(CLIENT_ID, CLIENT_SECRET)
    data = {'grant_type': 'client_credentials'}
    headers = {'User-Agent': USER_AGENT}
    
    res = requests.post('https://www.reddit.com/api/v1/access_token', 
                       auth=auth, data=data, headers=headers)
    
    if res.status_code != 200:
        raise Exception(f"OAuth failed: {res.status_code} {res.text}")
    
    return res.json()['access_token']

def get_queries(symbol):
    """Generate search queries for a symbol using yfinance."""
    try:
        t = yf.Ticker(symbol)
        name = t.info.get('shortName') or t.info.get('longName')
    except:
        name = None
    
    if not name:
        print(f"Warning: Could not fetch name for {symbol}. Using ticker only.")
        return [f'"{symbol}"', f'"${symbol}"']
    
    # Remove common suffixes
    clean_name = re.sub(r"(\s+(Inc\.?|Corp\.?|Corporation|Ltd\.?|PLC|Group|Holdings|Co\.?))\b", 
                       "", name, flags=re.IGNORECASE).strip()
    
    queries = [
        f'"{symbol}"',
        f'"${symbol}"',
        f'"{clean_name}"',
        f'"{clean_name.title()}"',
        f'"{clean_name.lower()}"'
    ]
    
    return list(set(queries))

def script_scrape_reddit(symbol: str = None):
    """Main Reddit scraping function with incremental support."""
    if symbol is None:
        symbol = "META"  # Will be replaced by daily_pipeline_reddit.py
    
    print(f"{'='*60}")
    print(f"Reddit Scraping Script Start - Symbol: {symbol}")
    print(f"{'='*60}")
    
    # Initialize database manager
    db_manager = DatabaseManager(DATABASE_PATH)
    
    # Authenticate
    token = get_reddit_token()
    print(f"✓ Successfully authenticated! Token: {token[:10]}...")
    
    # Get search queries
    queries = get_queries(symbol)
    url = f"https://oauth.reddit.com/r/{SUBREDDIT}/search.json"
    print(f"Generated {len(queries)} queries for {symbol}: {queries}")
    
    # Scraping parameters
    TARGET_POSTS = REDDIT_CONFIG['target_posts']
    MAX_PAGES = REDDIT_CONFIG['max_pages']
    SLEEP_SEC = REDDIT_CONFIG['sleep_sec']
    
    # Get last post ID for incremental scraping
    last_post_id = db_manager.get_last_post_id(symbol, source='reddit', subreddit=SUBREDDIT)
    after = last_post_id
    
    if after:
        print(f"✓ Incremental scraping - resuming from post: {after}")
    else:
        print(f"• First scrape for {symbol}")
    
    all_unique_posts = {}
    
    print(f"--- Starting Scraping for {symbol} ---")
    
    headers = {
        'User-Agent': USER_AGENT,
        'Authorization': f'bearer {token}'
    }
    
    for query in queries:
        print(f"\n--- Scraping query: {query} ---")
        
        after_query = after  # Reset for each query
        pages_scraped = 0
        
        while pages_scraped < MAX_PAGES and len(all_unique_posts) < TARGET_POSTS:
            params = {
                "q": query,
                "restrict_sr": "1",
                "sort": "new",
                "limit": "100",
                "after": after_query,
                "include_over_18": "on",
                "t": "all"
            }
            
            try:
                res = requests.get(url, headers=headers, params=params)
                
                if res.status_code == 429:
                    print("⚠ Rate limited. Sleep for 5 seconds...")
                    time.sleep(5)
                    continue
                
                res.raise_for_status()
                data = res.json()
                
                children = data.get("data", {}).get("children", [])
                if not children:
                    print("  No more results found")
                    break
                
                new_posts = 0
                for child in children:
                    post_id = child['data']['name']
                    if post_id not in all_unique_posts:
                        all_unique_posts[post_id] = child['data']
                        new_posts += 1
                
                after_query = data.get("data", {}).get("after")
                pages_scraped += 1
                
                print(f"  Page {pages_scraped}: Found {len(children)} posts ({new_posts} new). Total: {len(all_unique_posts)}")
                
                if not after_query:
                    print("  Reached the end of the stream.")
                    break
                
                time.sleep(SLEEP_SEC)
                
            except Exception as e:
                print(f"✗ Error on page {pages_scraped}: {e}")
                break
    
    print(f"\n--- Finished scraping. Collected {len(all_unique_posts)} new posts ---")
    
    if not all_unique_posts:
        print("✓ No new posts to save.")
        return
    
    # Prepare posts for database insertion
    posts_data = []
    for post_id, post in all_unique_posts.items():
        created_utc = post.get('created_utc', 0)
        timestamp_iso = ''
        if created_utc:
            try:
                timestamp_iso = datetime.fromtimestamp(created_utc, tz=timezone.utc).isoformat()
            except:
                timestamp_iso = ''
        
        posts_data.append({
            'post_id': post.get('name', ''),
            'symbol': symbol,
            'title': post.get('title', ''),
            'text': post.get('selftext') or post.get('url', ''),
            'score': post.get('score', 0),
            'comments': post.get('num_comments', 0),
            'timestamp_raw': created_utc,
            'timestamp_iso': timestamp_iso,
            'subreddit': SUBREDDIT
        })
    
    # Insert into database
    inserted = db_manager.insert_reddit_posts_batch(posts_data)
    print(f"✓ Inserted {inserted} posts into database")
    
    # Update metadata with last post ID
    if all_unique_posts:
        most_recent_id = list(all_unique_posts.keys())[0]
        db_manager.update_scrape_metadata(
            symbol=symbol,
            last_post_id=most_recent_id,
            posts_count=inserted,
            source='reddit',
            subreddit=SUBREDDIT
        )
        print(f"✓ Updated scrape metadata for {symbol}")
    
    print(f"\n{'='*60}")
    print("Script Finished Successfully")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    script_scrape_reddit()