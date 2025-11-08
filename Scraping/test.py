from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    symbol = "AAPL"
    url = f"https://stocktwits.com/symbol/{symbol}"
    page.goto(f"{url}")
    print(page.title())
    print("\nScrolling to load more messages...")
    for i in range(5):  # adjust 4–12 depending on how much you want
        page.mouse.wheel(0, 3000)  # scroll down
        time.sleep(2)  # let new messages load
        print("Done scrolling.\n")  
    time.sleep(30)
    html = page.content()
    print(html)
    browser.close()