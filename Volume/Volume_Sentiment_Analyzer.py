import os
import pandas as pd
from datetime import datetime

#Change CSV_PATH ofc
CSV_PATH = r"C:\Users\nmrva\OneDrive\Desktop\Screening and Scraping\data\raw\reddit\NVDA\2025\12\03\reddit_posts_NVDA_20251203.csv"

df = pd.read_csv(CSV_PATH)

df['timestamp_iso'] = df['timestamp_iso'].replace('', pd.NA)
df['ts'] = pd.to_datetime(df['timestamp_iso'], errors='coerce', utc=True)
df = df.dropna(subset=['ts'])

# Daily table per symbol
def daily_volume_table(df, symbol):
    sdf = df[df['symbol'] == symbol].copy()
    # Ensure ts is datetime just in case
    sdf['ts'] = pd.to_datetime(sdf['ts'])
    sdf['date_utc'] = sdf['ts'].dt.date
    
    def _summ(g):
        n = len(g)
        tmin = g['ts'].min()
        tmax = g['ts'].max()
        
        # 1. Real Duration (For display)
        real_duration_min = (tmax - tmin).total_seconds() / 60.0
        
        # 2. Math Duration (Enforce 1.0 min floor)
        math_duration_min = max(real_duration_min, 1.0)
        
        # We run into small sample variance problem quite easily, due to low volume
        # If we have fewer than 5 messages, the "window" is likely coincidence.
        # So we force the rate to be the Daily Average (Background Noise).
        if n < 5:
            # Example: 4 messages / 24 hours = 0.16 (Low/Quiet)
            rate = n / 24.0  
        else:
            # We have enough data to trust the window
            # Calculate true Burst Velocity
            rate = (n / math_duration_min) * 60.0
        
        return pd.Series({
            'messages': n,
            'tmin_utc': tmin,
            'tmax_utc': tmax,
            'window_minutes': round(real_duration_min, 2),
            'msgs_per_hour': round(rate, 3), 
            'avg_seconds_between': round((tmax - tmin).total_seconds()/max(n-1,1), 2),
        })

    return (sdf.groupby('date_utc').apply(_summ, include_groups=False).reset_index()
            .assign(symbol=symbol)
            .loc[:, ['symbol','date_utc','messages','tmin_utc','tmax_utc',
                     'window_minutes','msgs_per_hour','avg_seconds_between']]
            .sort_values(['symbol','date_utc'])
            .reset_index(drop=True))

# Detect source from CSV path (reddit or stocktwits)
if 'reddit' in CSV_PATH.lower():
    source = 'reddit'
elif 'stocktwits' in CSV_PATH.lower():
    source = 'stocktwits'
else:
    # Default to stocktwits if can't detect
    source = 'stocktwits'
    print(f"Warning: Could not detect source from path, defaulting to 'stocktwits'")

OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'volume_history', source))
os.makedirs(OUTPUT_DIR, exist_ok=True)

print("OUTPUT_DIR:", OUTPUT_DIR)
print("Reading:", CSV_PATH)
print("Total rows:", len(df))
print("Rows with valid ts:", df['ts'].notna().sum())
print("Symbols found:", sorted(df['symbol'].dropna().unique().tolist()))

def _to_iso_utc(s):
    return pd.to_datetime(s, utc=True).dt.strftime('%Y-%m-%dT%H:%M:%SZ')

def save_or_append_daily(daily_df: pd.DataFrame, output_dir: str = OUTPUT_DIR) -> str | None:
    if daily_df.empty:
        return None
    daily_df = daily_df.copy()
    daily_df['date_utc'] = daily_df['date_utc'].astype(str)
    daily_df['tmin_utc'] = _to_iso_utc(daily_df['tmin_utc'])
    daily_df['tmax_utc'] = _to_iso_utc(daily_df['tmax_utc'])

    symbol = daily_df['symbol'].iloc[0]
    out_path = os.path.join(output_dir, f"{symbol}.csv")

    if os.path.exists(out_path):
        try:
            existing = pd.read_csv(out_path)
        except Exception:
            existing = pd.DataFrame(columns=daily_df.columns)
        merged = pd.concat([existing, daily_df], ignore_index=True)
        merged = merged.drop_duplicates(subset=['date_utc'], keep='last').sort_values('date_utc')
        merged.to_csv(out_path, index=False)
    else:
        daily_df.to_csv(out_path, index=False)
    return out_path

# Write out per-ticker daily stats
symbols = sorted(df['symbol'].dropna().unique().tolist())
print("Final OUTPUT_DIR:", OUTPUT_DIR)
print("Symbols to write:", symbols)
for sym in symbols:
    daily = daily_volume_table(df, sym)
    if daily.empty:
        print(f"{sym}: no daily rows, skipping")
        continue
    out_path = save_or_append_daily(daily, OUTPUT_DIR)
    print(f"Saved {sym} daily volume stats -> {out_path}")