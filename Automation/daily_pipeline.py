import os
import re
import glob
import time
import subprocess
from datetime import datetime
from pathlib import Path

SYMBOLS = ["DGXX", "AAPL", "IREN"] 

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRAPE = PROJECT_ROOT / "Scraping" / "scraping_stockwits.py"
SENTI  = PROJECT_ROOT / "Sentiment_Analysis" / "stockwits_sentiment_analyzer.py"
VOLUME = PROJECT_ROOT / "Volume" / "Volume_Sentiment_Analyzer.py"

def replace_in_file(path: Path, pattern: str, repl: str, flags=re.M):
    text = path.read_text(encoding="utf-8")
    new_text, n = re.subn(pattern, repl, text, flags=flags)
    if n == 0:
        print(f"⚠ No matches when updating {path.name} with pattern: {pattern}")
    path.write_text(new_text, encoding="utf-8")
    return n

def latest_csv_for_symbol(symbol: str) -> str | None:
    today = datetime.utcnow()
    day_dir = PROJECT_ROOT / "data" / "raw" / "stocktwits" / f"{today:%Y}" / f"{today:%m}" / f"{today:%d}"
    files = glob.glob(str(day_dir / f"stocktwits_messages_{symbol}_*.csv"))
    if not files:
        return None
    return max(files, key=os.path.getmtime)

def run_script(path: Path):
    print(f"\nRunning {path.name} ...")
    subprocess.run(["python", str(path)], cwd=PROJECT_ROOT, check=True)
    print(f"✓ {path.name} finished")

def run_pipeline():
    print("=" * 80)
    print(f"Daily pipeline started @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    ok = []
    failed = []

    for sym in SYMBOLS:
        print("\n" + "-" * 80)
        print(f"Symbol: {sym}")
        print("-" * 80)

        try:
            # 1) Set symbol in scraper and run it
            replace_in_file(
                SCRAPE,
                r'^(\s*)symbol\s*=\s*r?["\'][^"\']*["\']',
                rf'\1symbol = "{sym}"'
            )
            
            run_script(SCRAPE)
            time.sleep(2)  # allow filesystem to flush

            # Resolve the CSV just created
            csv_path = latest_csv_for_symbol(sym)
            if not csv_path:
                raise RuntimeError(f"No CSV found for {sym} in today's folder.")
            print(f"CSV: {csv_path}")

            # Point sentiment script to CSV and run
            escaped_csv = csv_path.replace("\\", "\\\\")
            replace_in_file(
                SENTI,
                r'^(\s*)CSV_PATH\s*=\s*r?["\'][^"\']*["\']',
                rf'\1CSV_PATH = r"{escaped_csv}"'
            )

            run_script(SENTI)

            # 4) Point volume script to CSV and run
            escaped_csv = csv_path.replace("\\", "\\\\")
            replace_in_file(
                VOLUME,
                r'^(\s*)CSV_PATH\s*=\s*r?["\'][^"\']*["\']',
                rf'\1CSV_PATH = r"{escaped_csv}"'
            )

            run_script(VOLUME)

            ok.append(sym)
            print(f"✓ Done: {sym}")

        except subprocess.CalledProcessError as e:
            print(f"✗ Script failed for {sym}: {e}")
            failed.append(sym)
        except Exception as e:
            print(f"✗ Error for {sym}: {e}")
            failed.append(sym)

    # AI generated prints
    print("\n" + "=" * 80)
    print("PIPELINE SUMMARY")
    print("=" * 80)
    print(f"Total: {len(SYMBOLS)}")
    print(f"Success: {len(ok)} -> {', '.join(ok) if ok else '-'}")
    print(f"Failed:  {len(failed)} -> {', '.join(failed) if failed else '-'}")
    print("=" * 80)

if __name__ == "__main__":
    run_pipeline()