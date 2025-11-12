from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
import re
import os
import time
import csv

def normalize_time(raw, now = None):
    now = now or datetime.now(timezone.utc)
    if not raw:
        return None
    try:
        # ISO like 2025-10-29T15:34:02Z or +00:00
        return datetime.fromisoformat(raw.replace('Z', '+00:00')).isoformat()
    except Exception:
        pass

    m = re.match(r'^\s*(\d+)\s*([smhd])\s*$', raw, re.I)  # 9m, 2h, 1d, 30s

    if m:
        n, u = int(m.group(1)), m.group(2).lower()
        d = {'s': timedelta(seconds=n), 'm': timedelta(minutes=n), 'h': timedelta(hours=n), 'd': timedelta(days=n)}[u]
        return (now - d).isoformat()
    return raw

def script_scrape_stockwits():
    print("Script Start")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        symbol = "NVDA"
        url = f"https://stocktwits.com/symbol/{symbol}"
        print ("Navigating to Symbol Stock Page...")
        page.goto(url)
        time.sleep(10)
        cookies_button = page.get_by_role("button", name = "I Accept")
        match_count = cookies_button.count()
        print(f"Button: Found {match_count} matches")
            
    
        # Check if the button is visible
        if cookies_button.is_visible():
            print("Found the 'cookies' button! Clicking it now...")
            cookies_button.click()
            print("Button clicked successfully!")
                    
            # Wait to see the result and check if we get blocked
            print("Waiting 10 seconds to observe the page behavior...")
            time.sleep(5)

        # Scroll down multiple times to load more messages
        print("\nScrolling to load more messages...")
        for i in range(8):  # adjust 4–12 depending on how much you want
            page.mouse.wheel(0, 3000)  # scroll down
            time.sleep(2)  # let new messages load
            print("Done scrolling.\n")  
        
        soup = BeautifulSoup(page.content(), 'html.parser')
        message_divs = soup.find_all('div', class_ = 'RichTextMessage_body__4qUeP')
        print (f"Found {len(message_divs)} messages on this page")

        for i, div in enumerate(message_divs, 1):
            message_text = div.get_text(strip = True)
            print(f"Message {i}:")
            print(f"    {message_text}")

        else:            
            print("Cookies button not found")
    
        now_utc = datetime.now(timezone.utc)
        # Finding the timestamps of the messages, and creating the messages list
        messages = []
        for i, body in enumerate(message_divs, 1):
            text = body.get_text(separator=' ', strip=True)

            # 1) Go to the enclosing article of this message
            art = body.find_parent('article', class_=re.compile(r'^StreamMessage_article'))
            
            time_tag = None
            if art:
                # 2) Most precise: permalink time in the header
                time_tag = art.select_one('a[href*="/message/"] > time')
                # 3) Fallbacks inside the article (covers slight template changes)
                if not time_tag:
                    time_tag = art.select_one('time[datetime]')
                if not time_tag:
                    time_tag = art.find('time')

            raw_time = (time_tag.get('datetime') or
                        time_tag.get('title') or
                        time_tag.get_text(strip=True) or
                        time_tag.get('aria-label') if time_tag else None)

            iso_time = normalize_time(raw_time, now = now_utc)

            messages.append({
                'index': i,
                'symbol': symbol,
                'message': text,
                'timestamp_raw': raw_time or '',
                'timestamp_iso': iso_time or ''
            })
            print(f"Message {i}:\n    {message_text}")

        
        # Save to data/raw/stocktwits/YYYY/MM/DD/
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        today = datetime.utcnow()
        out_dir = os.path.join(project_root, 'data', 'raw', 'stocktwits', f"{today:%Y}", f"{today:%m}", f"{today:%d}")
        os.makedirs(out_dir, exist_ok=True)
        filename = os.path.join(out_dir, f"stocktwits_messages_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['index', 'symbol', 'message', 'timestamp_raw', 'timestamp_iso'])
            writer.writeheader()
            writer.writerows(messages)
        print(f"\nSaved {len(messages)} messages to {filename}")

        browser.close()
        print("Script Finished")

if __name__ == "__main__":
    script_scrape_stockwits()