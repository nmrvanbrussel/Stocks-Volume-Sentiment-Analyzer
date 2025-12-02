import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import glob
import re
from datetime import datetime, timedelta
from pathlib import Path

# ==============================================================================
# HOW TO RUN
# 1. Terminal: cd "C:\Users\nmrva\OneDrive\Desktop\Screening and Scraping"
# 2. Run: streamlit run Dashboard/dashboard_test.py
# ==============================================================================

# --- CONFIGURATION ---
st.set_page_config(page_title="Market Sentiment Dashboard", layout="wide")
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# --- LOAD DATA FUNCTIONS ---
@st.cache_data
def load_volume_data(source="stocktwits"):
    """Loads daily volume stats for all tickers."""
    folder = PROJECT_ROOT / "data" / "volume_history" / source
    all_files = glob.glob(str(folder / "*.csv"))
    
    df_list = []
    for f in all_files:
        try:
            temp_df = pd.read_csv(f)
            temp_df["source"] = source
            df_list.append(temp_df)
        except Exception:
            continue
            
    if not df_list:
        return pd.DataFrame()
    
    df = pd.concat(df_list, ignore_index=True)
    if "date_utc" in df.columns:
        df["date_utc"] = pd.to_datetime(df["date_utc"])
    return df

@st.cache_data
def load_sentiment_summary(ticker, source="stocktwits"):
    """Loads the summary reports for a specific ticker."""
    reports_root = PROJECT_ROOT / f"reports_{source}"
    files = list(reports_root.rglob("*summary*finbert*.csv"))
    
    df_list = []
    for f in files:
        try:
            match = re.search(r"(\d{8})", f.name)
            if not match: continue
            
            date_str = match.group(1)
            dt_obj = datetime.strptime(date_str, "%Y%m%d")

            temp = pd.read_csv(f)
            temp.columns = [c.lower() for c in temp.columns]
            
            if "symbol" in temp.columns:
                temp["symbol"] = temp["symbol"].astype(str).str.upper()
                temp = temp[temp["symbol"] == ticker]
            
            if not temp.empty:
                temp["date"] = dt_obj
                df_list.append(temp)
        except Exception:
            continue
            
    if not df_list:
        return pd.DataFrame()
        
    return pd.concat(df_list, ignore_index=True).sort_values("date")

@st.cache_data
def load_detailed_sentiment(ticker, source="stocktwits"):
    """
    Loads per-post sentiment data (e.g., reddit_posts_NVDA_..._with_finbert.csv)
    to calculate daily average sentiment from granular data.
    """
    # Path: data/processed/finbert/{source}/{ticker}/YYYY/MM/DD/...
    # Or your specific structure: data/processed/finbert/{source}/{ticker}/...
    # We will search recursively under data/processed
    
    processed_root = PROJECT_ROOT / "data" / "processed"
    
    # Pattern to match: *{ticker}*with_finbert.csv
    # This matches files like: reddit_posts_NVDA_20251130_with_finbert.csv
    files = list(processed_root.rglob(f"*{ticker}*with_finbert.csv"))
    
    df_list = []
    for f in files:
        try:
            temp = pd.read_csv(f)
            
            # Ensure we have the sentiment score column
            # Check for 'sentiment_signed' (from your CSV) or 'sentiment_score'
            if 'sentiment_signed' in temp.columns:
                score_col = 'sentiment_signed'
            elif 'sentiment_score' in temp.columns:
                score_col = 'sentiment_score'
            else:
                continue # Skip if no sentiment data
                
            # Extract date from timestamp_iso or filename
            if 'timestamp_iso' in temp.columns:
                temp['date'] = pd.to_datetime(temp['timestamp_iso']).dt.date
            else:
                # Fallback to filename date
                match = re.search(r"(\d{8})", f.name)
                if match:
                    temp['date'] = datetime.strptime(match.group(1), "%Y%m%d").date()
                else:
                    continue

            # We only need Date and Score for aggregation
            subset = temp[['date', score_col]].copy()
            subset.rename(columns={score_col: 'score'}, inplace=True)
            df_list.append(subset)
            
        except Exception:
            continue
            
    if not df_list:
        return pd.DataFrame()
    
    combined = pd.concat(df_list, ignore_index=True)
    
    # Group by Date to get Daily Average
    daily_sent = combined.groupby('date')['score'].mean().reset_index()
    daily_sent = daily_sent.sort_values('date')
    
    return daily_sent

# --- DASHBOARD LAYOUT ---

st.title("📈 AI-Driven Market Sentiment Dashboard")

# 1. Sidebar Setup
st.sidebar.header("Data Selection")
data_source = st.sidebar.radio("Data Source", ["stocktwits", "reddit"])

# 2. Load Volume Data (Master List)
volume_df = load_volume_data(data_source)

if volume_df.empty:
    st.error(f"No volume data found in 'data/volume_history/{data_source}'. Please run your pipeline first.")
    st.stop()

# 3. Ticker Selection
unique_tickers = sorted(volume_df["symbol"].unique())
selected_ticker = st.sidebar.selectbox("Select Ticker", unique_tickers)

# 4. Filter Data for Ticker
ticker_vol = volume_df[volume_df["symbol"] == selected_ticker].sort_values("date_utc")
ticker_sent_summary = load_sentiment_summary(selected_ticker, data_source)
ticker_sent_daily = load_detailed_sentiment(selected_ticker, data_source)

# 5. DATE RANGE FILTER
st.sidebar.markdown("---")
st.sidebar.header("Timeframe")

if not ticker_vol.empty:
    min_date = ticker_vol["date_utc"].min().date()
    max_date = ticker_vol["date_utc"].max().date()
else:
    min_date = datetime.now().date()
    max_date = datetime.now().date()

try:
    start_date, end_date = st.sidebar.date_input(
        "Select Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
except ValueError:
    st.sidebar.error("Please select a valid range.")
    start_date, end_date = min_date, max_date

# 6. Apply Filter
mask_vol = (ticker_vol['date_utc'].dt.date >= start_date) & (ticker_vol['date_utc'].dt.date <= end_date)
filtered_vol = ticker_vol.loc[mask_vol]

if not ticker_sent_summary.empty:
    mask_sent = (ticker_sent_summary['date'].dt.date >= start_date) & (ticker_sent_summary['date'].dt.date <= end_date)
    filtered_sent_summary = ticker_sent_summary.loc[mask_sent]
else:
    filtered_sent_summary = pd.DataFrame()

if not ticker_sent_daily.empty:
    # Ensure date column is datetime for filtering
    ticker_sent_daily['date'] = pd.to_datetime(ticker_sent_daily['date'])
    mask_daily = (ticker_sent_daily['date'].dt.date >= start_date) & (ticker_sent_daily['date'].dt.date <= end_date)
    filtered_sent_daily = ticker_sent_daily.loc[mask_daily]
else:
    filtered_sent_daily = pd.DataFrame()


# --- KPI METRICS ---
col1, col2, col3, col4 = st.columns(4)

latest_vol_row = filtered_vol.iloc[-1] if not filtered_vol.empty else None

with col1:
    if latest_vol_row is not None:
        st.metric("Total Messages (Period)", f"{int(filtered_vol['messages'].sum())}")
    else:
        st.metric("Total Messages", "0")

with col2:
    if latest_vol_row is not None:
        if 'msgs_per_hour' in latest_vol_row:
            st.metric("Latest Velocity", f"{latest_vol_row['msgs_per_hour']:.2f}")
        else:
            st.metric("Latest Velocity", "N/A")
    else:
        st.metric("Velocity", "N/A")

with col3:
    if not filtered_sent_daily.empty:
        latest_s = filtered_sent_daily.iloc[-1]
        st.metric("Daily Sentiment", f"{latest_s['score']:.4f}")
    elif not filtered_sent_summary.empty:
        latest_s = filtered_sent_summary.iloc[-1]
        st.metric("Sentiment Score", f"{latest_s['sentiment_mean']:.4f}")
    else:
        st.metric("Sentiment Score", "N/A")

with col4:
    st.metric("Source", data_source.capitalize())

# --- CHARTS ---

tab1, tab2 = st.tabs(["📊 Volume & Velocity", "🧠 Sentiment Analysis"])

with tab1:
    st.subheader(f"Volume Analysis: {selected_ticker}")
    
    if not filtered_vol.empty:
        # CHART 1: Total Message Volume
        st.markdown("### 📢 Daily Message Volume")
        fig_vol = px.bar(
            filtered_vol, 
            x='date_utc', 
            y='messages',
            title="Total Messages per Day",
            labels={'messages': 'Message Count', 'date_utc': 'Date'},
            color_discrete_sequence=['#00CC96']
        )
        fig_vol.update_layout(hovermode="x unified")
        st.plotly_chart(fig_vol, use_container_width=True)
        
        # CHART 2: Velocity
        st.markdown("### ⚡ Discussion Velocity")
        y_col = 'msgs_per_hour' if 'msgs_per_hour' in filtered_vol.columns else 'daily_avg_rate'
        
        fig_vel = px.line(
            filtered_vol, 
            x='date_utc', 
            y=y_col,
            title="Velocity (Intensity of Discussion)",
            labels={y_col: 'Rate', 'date_utc': 'Date'},
            markers=True,
            line_shape='linear'
        )
        fig_vel.update_traces(line_color='#636EFA', line_width=3)
        fig_vel.update_layout(hovermode="x unified")
        st.plotly_chart(fig_vel, use_container_width=True)

    else:
        st.info("No volume data available for this date range.")

with tab2:
    st.subheader(f"Sentiment Trends: {selected_ticker}")
    
    # 1. Daily Average Sentiment (From detailed posts)
    if not filtered_sent_daily.empty:
        st.markdown("### 📉 Daily Average Sentiment (Aggregated from Posts)")
        fig_daily = px.line(
            filtered_sent_daily, 
            x='date', 
            y='score', 
            title="Daily Sentiment Score (-1 to +1)",
            markers=True
        )
        fig_daily.add_hline(y=0, line_dash="dash", line_color="gray")
        fig_daily.update_traces(line_color='#FF5733', line_width=3)
        st.plotly_chart(fig_daily, use_container_width=True)
    
    # 2. Composition (From Summary Reports)
    if not filtered_sent_summary.empty:
        st.markdown("### 📊 Bullish vs Bearish Composition")
        if 'pos_share' in filtered_sent_summary.columns:
            fig_share = go.Figure()
            fig_share.add_trace(go.Bar(x=filtered_sent_summary['date'], y=filtered_sent_summary['pos_share'], name='Bullish', marker_color='#2ca02c'))
            fig_share.add_trace(go.Bar(x=filtered_sent_summary['date'], y=filtered_sent_summary['neg_share'], name='Bearish', marker_color='#d62728'))
            fig_share.add_trace(go.Bar(x=filtered_sent_summary['date'], y=filtered_sent_summary['neu_share'], name='Neutral', marker_color='#7f7f7f'))
            
            fig_share.update_layout(barmode='stack', title="Daily Sentiment Composition")
            st.plotly_chart(fig_share, use_container_width=True)
        else:
            st.write("Sentiment breakdown columns missing.")
            
    if filtered_sent_daily.empty and filtered_sent_summary.empty:
        st.warning(f"No sentiment data found for {selected_ticker}.")

# --- RAW DATA EXPANDER ---
with st.expander("View Raw Data Tables"):
    st.write("### Volume Data", filtered_vol)
    if not filtered_sent_daily.empty:
        st.write("### Daily Sentiment (Aggregated)", filtered_sent_daily)
    if not filtered_sent_summary.empty:
        st.write("### Sentiment Summary Reports", filtered_sent_summary)