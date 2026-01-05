import requests
import time
import re
import os
import csv
import yfinance as yf
from datetime import datetime, timezone
from dotenv import load_dotenv
from pathlib import Path
import pandas as pd

#Gotta fix the queries, its too specific we need it without quotations this is how reddit defines it. 

print("Scraping Tags Reddit Script Start")
# Load environment variables from .env file in project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
env_path = PROJECT_ROOT / ".env"
load_dotenv(dotenv_path=env_path)

# Get credentials from environment
CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
USER_AGENT = os.getenv("REDDIT_USER_AGENT", "wsb-ticker-scraper/0.1 by Niels van Brussel")

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
    
    symbol = "NVDA"  # Will be replaced by daily_pipeline_reddit.py
    
    # Authenticate
    token = get_reddit_token()
    print(f"Successfully authenticated! Token: {token[:10]}...")
    
    # Get search queries
    queries = get_queries(symbol)
    url = f"https://oauth.reddit.com/r/all/search.json"
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
                "restrict_sr": "0",
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

if __name__ == "__main__":
    script_scrape_reddit()