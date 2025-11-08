from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time
import csv

def script_scrape_stockwits_test():
    print("Script Start")
    with sync_playwright() as p:
        # Launch browser in non-headless mode so we can see what's happening
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        print("Navigating to StockTwits Sentiment page...")
        page.goto('https://stocktwits.com/sentiment')
        
        # Wait a few seconds for the page to fully load
        print("Waiting for page to load...")
        time.sleep(3)
        
        try:
            # Look for the "equities" tab button
            # We'll use the text content to find it since that's most reliable
            print("Looking for the 'equities' button...")
            equities_button = page.locator("text=equities")
            
            # Check if the button is visible
            if equities_button.is_visible():
                print("Found the 'equities' button! Clicking it now...")
                equities_button.click()
                print("Button clicked successfully!")
                
                # Wait to see the result and check if we get blocked
                print("Waiting 10 seconds to observe the page behavior...")
                time.sleep(10)
                
                # Get the page content after clicking to see if anything changed
                html = page.content()
                print("Page loaded successfully. Checking for blocks or rate limits...")
                
                # Check for common blocking indicators
                if "captcha" in html.lower():
                    print("⚠️ WARNING: CAPTCHA detected!")
                elif "rate limit" in html.lower() or "too many requests" in html.lower():
                    print("⚠️ WARNING: Rate limit message detected!")
                elif "access denied" in html.lower() or "blocked" in html.lower():
                    print("⚠️ WARNING: Access blocked!")
                else:
                    print("✓ No obvious blocking detected. Page seems to be working!")
                
            else:
                print("Button not visible yet. Page might still be loading...")
                
        except Exception as e:
            print(f"Error occurred: {e}")
        
        # Keep browser open for a bit so you can manually inspect
        print("Keeping browser open for 30 more seconds for you to inspect...")
        time.sleep(10)
        
        print("Closing browser...")
        browser.close()
        print("Script finished!")


if __name__ == "__main__":
    script_scrape_stockwits_test()