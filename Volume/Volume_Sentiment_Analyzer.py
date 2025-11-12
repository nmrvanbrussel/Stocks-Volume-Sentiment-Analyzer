import os
import pandas as pd
from datetime import datetime

#Change CSV_PATH ofc
CSV_PATH = r"C:\Users\nmrva\OneDrive\Desktop\Screening and Scraping\data\raw\stocktwits\2025\11\12\stocktwits_messages_NVDA_20251112_162003.csv"

df = pd.read_csv(CSV_PATH)

df['timestamp_iso'] = df['timestamp_iso'].replace('', pd.NA)
df['ts'] = pd.to_datetime(df['timestamp_iso'], errors='coerce', utc=True)
df = df.dropna(subset=['ts'])

# Daily table per symbol
def daily_volume_table(df, symbol):
    sdf = df[df['symbol'] == symbol].copy()
    sdf['date_utc'] = sdf['ts'].dt.date
    def _summ(g):
        n = len(g); tmin = g['ts'].min(); tmax = g['ts'].max()
        win_min = max((tmax - tmin).total_seconds()/60.0, 1e-9)
        return pd.Series({
            'messages': n,
            'tmin_utc': tmin,
            'tmax_utc': tmax,
            'window_minutes': round(win_min, 2),
            'msgs_per_hour': round((n/win_min)*60.0, 3),
            'avg_seconds_between': round((tmax - tmin).total_seconds()/max(n-1,1), 2),
        })
    return (sdf.groupby('date_utc').apply(_summ).reset_index()
            .assign(symbol=symbol)
            .loc[:, ['symbol','date_utc','messages','tmin_utc','tmax_utc',
                     'window_minutes','msgs_per_hour','avg_seconds_between']]
            .sort_values(['symbol','date_utc'])
            .reset_index(drop=True))

OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'volume_history'))
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