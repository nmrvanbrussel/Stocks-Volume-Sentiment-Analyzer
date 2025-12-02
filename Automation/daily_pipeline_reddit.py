import os
import re
import glob
import time
import subprocess
from datetime import datetime
from pathlib import Path

SYMBOLS = [
    # Big Tech / Model Builders
    "NVDA", "AAPL", "GOOG", "MSFT", "META", "AMZN", "TSLA",
    
    # AI Hardware & Semis (The "Pick and Shovel" plays)
    "AMD", "TSM", "AVGO", "MU", "INTC", "ARM",
    
    # AI Infrastructure & Servers
    "SMCI", "DELL", "VRT","IREN"
    
    # AI Software & Data
    "PLTR", "SNOW", "SOUN"
]

SUBREDDITS = [
    # High Volume / Hype
    "wallstreetbets", 
    "SmallStreetBets",
    "StockMarket",
    "stocks",
    
    # Serious / Macro
    "investing",
    "SecurityAnalysis",
    "Economics",
    
    # Technical / Trading
    "options",
    "thetagang"
]

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REDDIT_SCRAPE = PROJECT_ROOT / "Scraping" / "scraping_reddit.py"
REDDIT_SENTI  = PROJECT_ROOT / "Sentiment_Analysis" / "reddit_sentiment_analyzer.py"
VOLUME = PROJECT_ROOT / "Volume" / "Volume_Sentiment_Analyzer.py"

def replace_in_file(path: Path, pattern: str, repl: str, flags=re.M):
    text = path.read_text(encoding="utf-8")
    new_text, n = re.subn(pattern, repl, text, flags=flags)
    if n == 0:
        print(f"⚠ No matches when updating {path.name} with pattern: {pattern}")
    path.write_text(new_text, encoding="utf-8")
    return n

def latest_csv_for_symbol(symbol: str, source: str = "reddit") -> str | None:
    """Get latest CSV for symbol from specified source (reddit or stocktwits)."""
    today = datetime.utcnow()
    day_dir = PROJECT_ROOT / "data" / "raw" / source / symbol / f"{today:%Y}" / f"{today:%m}" / f"{today:%d}"
    
    if source == "reddit":
        pattern = f"reddit_posts_{symbol}_*.csv"
    else:  # stocktwits
        pattern = f"stocktwits_messages_{symbol}_*.csv"
    
    files = glob.glob(str(day_dir / pattern))
    if not files:
        return None
    return max(files, key=os.path.getmtime)

def run_script(path: Path):
    print(f"\nRunning {path.name} ...")
    subprocess.run(["python", str(path)], cwd=PROJECT_ROOT, check=True)
    print(f"✓ {path.name} finished")

def run_pipeline():
    print("=" * 80)
    print(f"Reddit Daily Pipeline started @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    ok = []
    failed = []
    
    for sym in SYMBOLS:
        print("\n" + "#" * 80)
        print(f"STARTING PIPELINE FOR TICKER: {sym}")
        print("#" * 80)

        scraping_errors = False

        for sub in SUBREDDITS:
            print(f"\n--- Scraping {sym} in r/{sub} ---")

            try:
                # 1) Set SUBREDDIT in Reddit scraper and run it
                replace_in_file(
                    REDDIT_SCRAPE,
                    r'^(\s*)SUBREDDIT\s*=\s*r?["\'][^"\']*["\']',
                    rf'\1SUBREDDIT = "{sub}"'
                )
                # 2) Set symbol in Reddit scraper and run it
                replace_in_file(
                    REDDIT_SCRAPE,
                    r'^(\s*)symbol\s*=\s*r?["\'][^"\']*["\']',
                    rf'\1symbol = "{sym}"'
                )

                run_script(REDDIT_SCRAPE)
                time.sleep(2)  # allow filesystem to flush
            
            except Exception as e:
                print(f"✗ Scraping failed for {sym} in {sub}: {e}")
                scraping_errors = True

        print(f"\n Processing Combined Data for {sym}...")
        
        try:
            # Find the file we just filled up
            csv_path = latest_csv_for_symbol(sym, "reddit")
            if not csv_path:
                raise RuntimeError(f"No Reddit CSV found for {sym} (Scraping likely failed completely).")
            
            print(f"Target CSV: {csv_path}")

            # Update Sentiment Script Path
            escaped_csv = csv_path.replace("\\", "\\\\")
            replace_in_file(
                REDDIT_SENTI,
                r'^(\s*)CSV_PATH\s*=\s*r?["\'][^"\']*["\']',
                rf'\1CSV_PATH = r"{escaped_csv}"'
            )
            # Run FinBERT (Once per ticker)
            run_script(REDDIT_SENTI)

            # Update Volume Script Path
            replace_in_file(
                VOLUME,
                r'^(\s*)CSV_PATH\s*=\s*r?["\'][^"\']*["\']',
                rf'\1CSV_PATH = r"{escaped_csv}"'
            )
            # Run Volume Analysis (Once per ticker)
            run_script(VOLUME)

            if not scraping_errors:
                ok.append(sym)
                print(f"✓ FULL SUCCESS: {sym}")
            else:
                failed.append(f"{sym} (Partial)")
                print(f"⚠ PARTIAL SUCCESS: {sym} (Some subreddits failed)")

        except Exception as e:
            print(f"✗ Processing failed for {sym}: {e}")
            failed.append(f"{sym} (Processing)")

    # Pipeline summary
    print("\n" + "=" * 80)
    print("REDDIT PIPELINE SUMMARY")
    print("=" * 80)
    print(f"Total: {len(SYMBOLS)}")
    print(f"Success: {len(ok)} -> {', '.join(ok) if ok else '-'}")
    print(f"Failed:  {len(failed)} -> {', '.join(failed) if failed else '-'}")
    print("=" * 80)

if __name__ == "__main__":
    run_pipeline()

