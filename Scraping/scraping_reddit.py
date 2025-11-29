import requests
import time
import re
import os
import csv
import yfinance as yf
from datetime import datetime, timezone
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file in project root
project_root = Path(__file__).resolve().parent.parent
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)

# Get credentials from environment
CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
USER_AGENT = os.getenv("REDDIT_USER_AGENT", "wsb-ticker-scraper/0.1 by Niels van Brussel")
SUBREDDIT = ("wallstreetbets")

# Validate credentials
if not CLIENT_ID or not CLIENT_SECRET:
    raise ValueError("Reddit credentials not found in .env file. Please create .env file with REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET")

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

def script_scrape_reddit():
    """Main Reddit scraping function."""
    print("Reddit Scraping Script Start")
    
    symbol = "GOOG"  # Will be replaced by daily_pipeline_reddit.py
    
    # Authenticate
    token = get_reddit_token()
    print(f"Successfully authenticated! Token: {token[:10]}...")
    
    # Get search queries
    queries = get_queries(symbol)
    url = f"https://oauth.reddit.com/r/{SUBREDDIT}/search.json"
    print(f"Generated Queries for {symbol}: {queries}")
    
    # Scraping parameters
    TARGET_POSTS = 2000
    MAX_PAGES = 50
    SLEEP_SEC = 2
    
    all_unique_posts = {}
    
    print(f"--- Starting Scraping for {symbol} ---")
    
    headers = {
        'User-Agent': USER_AGENT,
        'Authorization': f'bearer {token}'
    }
    
    for query in queries:
        print(f"--- Started scraping for {query} ---")
        
        after = None
        pages_scraped = 0
        
        while pages_scraped < MAX_PAGES and len(all_unique_posts) < TARGET_POSTS:
            params = {
                "q": query,
                "restrict_sr": "1",
                "sort": "new",
                "limit": "100",
                "after": after,
                "include_over_18": "on",
                "t": "all"
            }
            
            try:
                res = requests.get(url, headers=headers, params=params)
                
                if res.status_code == 429:
                    print("Rate limited. Sleep for 5 seconds...")
                    time.sleep(5)
                    continue
                
                res.raise_for_status()
                data = res.json()
                
                children = data.get("data", {}).get("children", [])
                if not children:
                    print("No more results found")
                    break
                
                new_posts = 0
                for child in children:
                    post_id = child['data']['name']
                    if post_id not in all_unique_posts:
                        all_unique_posts[post_id] = child['data']
                        new_posts += 1
                
                after = data.get("data", {}).get("after")
                pages_scraped += 1
                
                print(f"Page {pages_scraped}: Found {len(children)} posts ({new_posts} new). Total Unique: {len(all_unique_posts)}")
                
                if not after:
                    print("Reached the end of the stream.")
                    break
                
                time.sleep(SLEEP_SEC)
                
            except Exception as e:
                print(f"Error on page {pages_scraped}: {e}")
                break
    
    print(f"\n--- Finished. Collected {len(all_unique_posts)} UNIQUE posts. ---")
    
    # Prepare data for CSV
    posts_data = []
    for i, post in enumerate(all_unique_posts.values(), 1):
        created_utc = post.get('created_utc', 0)
        timestamp_iso = ''
        if created_utc:
            try:
                timestamp_iso = datetime.fromtimestamp(created_utc, tz=timezone.utc).isoformat()
            except:
                timestamp_iso = ''
        
        posts_data.append({
            'index': i,
            'symbol': symbol,
            'title': post.get('title', ''),
            'text': post.get('selftext') or post.get('url', ''),
            'score': post.get('score', 0),
            'comments': post.get('num_comments', 0),
            'timestamp_raw': str(created_utc) if created_utc else '',
            'timestamp_iso': timestamp_iso,
            'post_id': post.get('name', '')
        })
    
    # Save to data/raw/reddit/{SYMBOL}/{YEAR}/{MONTH}/{DAY}/
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    today = datetime.utcnow()
    out_dir = os.path.join(project_root, 'data', 'raw', 'reddit', symbol, 
                          f"{today:%Y}", f"{today:%m}", f"{today:%d}")
    os.makedirs(out_dir, exist_ok=True)
    
    filename = os.path.join(out_dir, 
                           f"reddit_posts_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        if posts_data:
            writer = csv.DictWriter(f, fieldnames=posts_data[0].keys())
            writer.writeheader()
            writer.writerows(posts_data)
    
    print(f"\nSaved {len(posts_data)} posts to {filename}")
    print("Script Finished")

if __name__ == "__main__":
    script_scrape_reddit()

