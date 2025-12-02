import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import yfinance as yf
import os
import glob
import re
from datetime import datetime, timedelta
from pathlib import Path
from plotly.subplots import make_subplots

# ==============================================================================
# 1. APP CONFIGURATION
# ==============================================================================
st.set_page_config(
    page_title="Volume and Sentiment Project",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Clean, professional styling
st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    .metric-card {
        background-color: #161B22;
        border: 1px solid #30363D;
        border-radius: 6px;
        padding: 15px;
    }
    div[data-testid="stMetricValue"] { font-size: 24px; color: #E6EDF3; }
    div[data-testid="stMetricLabel"] { font-size: 14px; color: #8B949E; }
</style>
""", unsafe_allow_html=True)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ==============================================================================
# 2. DATA LOADING FUNCTIONS
# ==============================================================================
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
            temp_df.columns = [c.lower() for c in temp_df.columns]
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
    """
    Loads the summary reports for a specific ticker.
    UPDATED: 
    1. Removes duplicates if multiple runs occurred on the same day.
    2. Respects the 'date' column INSIDE the file if it exists (fixes the single-bar bug).
    """
    path_nested = PROJECT_ROOT / "reports" / source
    path_flat = PROJECT_ROOT / f"reports_{source}"
    
    sent_path = None
    if path_nested.exists():
        sent_path = path_nested
    elif path_flat.exists():
        sent_path = path_flat
    
    sent_dfs = []
    if sent_path:
        # Recursively find all summary files
        sent_files = list(sent_path.rglob("*summary*finbert*.csv"))
        # Sort files to ensure we process them in chronological order
        sent_files = sorted(sent_files)
        
        for f in sent_files:
            try:
                # 1. Extract Date from Filename (Fallback)
                match = re.search(r"(\d{8})", f.name)
                if not match: continue
                file_date_obj = datetime.strptime(match.group(1), "%Y%m%d")
                
                # 2. Read CSV
                temp = pd.read_csv(f)
                temp.columns = [c.lower() for c in temp.columns]
                
                if "symbol" in temp.columns:
                    temp["symbol"] = temp["symbol"].astype(str).str.upper()
                    
                # 3. Filter for Ticker
                temp = temp[temp["symbol"] == ticker]
                
                if not temp.empty:
                    # --- THE FIX: Priority Check for Internal Date ---
                    # If the analyzer saved a 'date' column, use it (it contains the real historical dates).
                    # If not, fall back to the filename date.
                    if "date" in temp.columns:
                        temp["date"] = pd.to_datetime(temp["date"])
                    else:
                        temp["date"] = file_date_obj
                        
                    sent_dfs.append(temp)
            except: continue
        
    sentiment_df = pd.concat(sent_dfs, ignore_index=True) if sent_dfs else pd.DataFrame()
    
    if not sentiment_df.empty:
        # --- DEDUPLICATION LOGIC ---
        # 1. Ensure date is datetime for sorting
        sentiment_df["date"] = pd.to_datetime(sentiment_df["date"])
        
        # 2. Sort by date
        sentiment_df = sentiment_df.sort_values("date")
        
        # 3. Drop Duplicates
        # If we have multiple rows for "Dec 2nd", keep the LAST one loaded (the most recent run)
        sentiment_df = sentiment_df.drop_duplicates(subset=['date', 'symbol'], keep='last')

    return sentiment_df

@st.cache_data
def load_detailed_sentiment(ticker, source="stocktwits"):
    """
    Loads per-post sentiment data to calculate daily average sentiment.
    FIXED: Now explicitly checks 'data/processed/finbert/{source}' which is where your analyzer saves files.
    """
    # 1. Try the specific path structure from your Reddit Analyzer (includes 'finbert')
    path_finbert = PROJECT_ROOT / "data" / "processed" / "finbert" / source
    # 2. Fallback to standard path
    path_standard = PROJECT_ROOT / "data" / "processed" / source
    
    processed_root = None
    if path_finbert.exists():
        processed_root = path_finbert
    elif path_standard.exists():
        processed_root = path_standard
    else:
        return pd.DataFrame()

    files = list(processed_root.rglob(f"*{ticker}*with_finbert.csv"))
    
    df_list = []
    for f in files:
        try:
            temp = pd.read_csv(f)
            
            # Identify the score column
            if 'sentiment_signed' in temp.columns:
                score_col = 'sentiment_signed'
            elif 'sentiment_score' in temp.columns:
                score_col = 'sentiment_score'
            else:
                continue 
                
            # Date extraction
            if 'timestamp_iso' in temp.columns:
                temp['date'] = pd.to_datetime(temp['timestamp_iso']).dt.date
            else:
                match = re.search(r"(\d{8})", f.name)
                if match:
                    temp['date'] = datetime.strptime(match.group(1), "%Y%m%d").date()
                else:
                    continue

            subset = temp[['date', score_col]].copy()
            subset.rename(columns={score_col: 'score'}, inplace=True)
            df_list.append(subset)
            
        except Exception:
            continue
            
    if not df_list:
        return pd.DataFrame()
    
    combined = pd.concat(df_list, ignore_index=True)
    
    # Group by Date for Daily Average
    daily_sent = combined.groupby('date')['score'].mean().reset_index()
    daily_sent['date'] = pd.to_datetime(daily_sent['date'])
    daily_sent = daily_sent.sort_values('date')
    
    return daily_sent

@st.cache_data
def get_stock_price(ticker, start, end):
    try:
        # Fetch history using yfinance
        df = yf.Ticker(ticker).history(start=start, end=end + timedelta(days=1))
        return df
    except Exception:
        return pd.DataFrame()

# ==============================================================================
# 3. PAGE: HOME / METHODOLOGY
# ==============================================================================
def render_home():
    st.title("Volume and Sentiment Project")
    st.markdown("### Technical Methodology & Architecture")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### NLP Model: FinBERT")
        st.markdown("""
        To accurately gauge investor sentiment, this project utilizes **FinBERT** (ProsusAI), a BERT language model specifically pre-trained on financial text.
        
        Unlike standard models trained on Wikipedia, FinBERT understands financial context (e.g., "bullish," "short," "put options").
        
        **Classification Logic:**
        Each scraped message is tokenized and passed through the model softmax layer to output probabilities for three classes:
        * **Positive** (e.g., "Buying the dip")
        * **Negative** (e.g., "Puts printed today")
        * **Neutral** (e.g., "Earnings are on Tuesday")
        
        The daily sentiment score is a weighted average of these probabilities across all messages for a given ticker.
        """)

    with col2:
        st.markdown("#### Velocity & The Small Sample Problem")
        st.markdown("""
        **The Goal:** Calculate message intensity (Messages per Hour) to detect viral bursts.
        
        **The Problem (Small Sample Variance):** If a stock has only 2 messages posted 2 minutes apart (pure coincidence), standard velocity math would calculate a rate of **60 messages/hour**. This creates massive false positive spikes on quiet days.
        
        **The Solution (Noise Filter):**
        We implemented a statistical threshold:
        * If **$n < 5$ messages**: The day is classified as "Low Activity." Velocity is defaulted to the Daily Average ($n/24$), flattening the spike.
        * If **$n \ge 5$ messages**: We calculate the true Burst Velocity based on the active time window.
        """)
        
        st.latex(r'''
        \text{Velocity} = \begin{cases} 
        n / 24 & \text{if } n < 5 \text{ (Noise)} \\
        (n / \text{ActiveMinutes}) \times 60 & \text{if } n \ge 5 \text{ (Signal)}
        \end{cases}
        ''')

    st.markdown("---")
    st.info("Navigate to **Terminal** in the sidebar to visualize the data.")

# ==============================================================================
# 4. PAGE: TERMINAL
# ==============================================================================
def render_terminal():
    st.title("Market Terminal")
    
    # --- SIDEBAR CONTROLS ---
    st.sidebar.header("Data Feed")
    data_source = st.sidebar.selectbox("Source", ["reddit", "stocktwits"], index=0)
    
    # Load Data
    vol_data = load_volume_data(data_source)
    
    if vol_data.empty:
        st.error(f"No volume data found for {data_source}. Please check your pipeline output.")
        st.stop()
        
    st.sidebar.header("Asset Selection")
    all_tickers = sorted(vol_data["symbol"].unique())
    ticker = st.sidebar.selectbox("Primary Ticker", all_tickers, index=0)
    
    # Load Sentiment Data for Selected Ticker
    ticker_sent_summary = load_sentiment_summary(ticker, data_source)
    ticker_sent_daily = load_detailed_sentiment(ticker, data_source)

    # Comparison Feature
    compare_mode = st.sidebar.checkbox("Compare Ticker?", value=False)
    ticker2 = None
    if compare_mode:
        ticker2 = st.sidebar.selectbox("Comparison Ticker", [t for t in all_tickers if t != ticker])

    st.sidebar.markdown("---")
    st.sidebar.header("View Settings")
    
    # Date Range
    if not vol_data.empty:
        min_date = vol_data["date_utc"].min().date()
        max_date = vol_data["date_utc"].max().date()
        # Default to full range
        start_d, end_d = st.sidebar.date_input("Date Range", [min_date, max_date])
    
    # Y-Axis Clipping
    st.sidebar.subheader("Chart Scaling")
    clip_outliers = st.sidebar.checkbox("Limit Velocity Y-Axis?", value=True)
    y_limit = None
    if clip_outliers:
        curr_max = vol_data[vol_data["symbol"]==ticker]['msgs_per_hour'].max() if not vol_data.empty else 100
        default_val = min(50.0, float(curr_max))
        y_limit = st.sidebar.slider("Max Velocity", 5.0, 500.0, default_val)

    # --- FILTERING LOGIC ---
    def filter_date(df, date_col):
        if df.empty or date_col not in df.columns:
            return pd.DataFrame()
        return df[(df[date_col].dt.date >= start_d) & (df[date_col].dt.date <= end_d)].copy()

    # Primary Ticker Data
    v1 = filter_date(vol_data[vol_data["symbol"] == ticker], "date_utc")
    # For sentiment, we filter the pre-loaded ticker-specific dataframes
    s_daily = filter_date(ticker_sent_daily, "date")
    s_summary = filter_date(ticker_sent_summary, "date")
    
    # Secondary Ticker Data
    v2 = pd.DataFrame()
    if ticker2:
        v2 = filter_date(vol_data[vol_data["symbol"] == ticker2], "date_utc")

    # --- KPI HEADER ---
    st.markdown(f"### {ticker} Analytics")
    k1, k2, k3, k4 = st.columns(4)
    
    def get_latest(df, col): return df.iloc[-1][col] if not df.empty else 0

    with k1: st.metric("Total Messages", f"{int(v1['messages'].sum())}" if not v1.empty else "0")
    with k2: st.metric("Peak Velocity", f"{v1['msgs_per_hour'].max():.2f}/hr" if not v1.empty else "0")
    with k3: st.metric("Latest Sentiment", f"{get_latest(s_summary, 'sentiment_mean'):.3f}" if not s_summary.empty else "N/A")
    with k4: st.metric("Bullish Share", f"{get_latest(s_summary, 'pos_share'):.1%}" if not s_summary.empty else "N/A")

    # --- CHART 0: PRICE ACTION ---
    st.markdown("---")
    st.subheader(f"Price Action ({ticker})")
    
    price_df = get_stock_price(ticker, start_d, end_d)
    
    if not price_df.empty:
        fig_price = go.Figure(data=[go.Candlestick(
            x=price_df.index,
            open=price_df['Open'],
            high=price_df['High'],
            low=price_df['Low'],
            close=price_df['Close'],
            name=ticker
        )])
        
        fig_price.update_layout(
            template="plotly_dark",
            height=350,
            margin=dict(l=10, r=10, t=30, b=10),
            xaxis_rangeslider_visible=False,
            hovermode="x unified",
            yaxis_title="Price"
        )
        st.plotly_chart(fig_price, use_container_width=True)
    else:
        st.warning(f"Could not load price data for {ticker}. Ensure the ticker is a valid Yahoo Finance symbol.")

    # --- CHART 1: DAILY MESSAGE VOLUME ---
    st.subheader("Daily Message Volume")
    
    if not v1.empty:
        fig_vol = go.Figure()
        
        fig_vol.add_trace(go.Bar(
            x=v1['date_utc'], y=v1['messages'],
            name=ticker,
            marker_color='#87CEFA'
        ))
        
        if not v2.empty:
            fig_vol.add_trace(go.Bar(
                x=v2['date_utc'], y=v2['messages'],
                name=ticker2,
                marker_color='#D033FF',
                opacity=0.8
            ))

        fig_vol.update_layout(
            template="plotly_dark", 
            height=350, 
            margin=dict(l=10, r=10, t=30, b=10),
            hovermode="x unified",
            barmode='group' 
        )
        st.plotly_chart(fig_vol, use_container_width=True)
    else:
        st.info("No volume data available.")

    # --- CHART 2: VELOCITY ---
    st.subheader("Hype Velocity (Messages/Hour)")
    
    if not v1.empty:
        fig_vel = go.Figure()
        
        fig_vel.add_trace(go.Scatter(
            x=v1['date_utc'], y=v1['msgs_per_hour'],
            mode='lines+markers', name=f"{ticker}",
            line=dict(color='#00F5FF', width=2), marker=dict(size=4)
        ))
        
        if not v2.empty:
            fig_vel.add_trace(go.Scatter(
                x=v2['date_utc'], y=v2['msgs_per_hour'],
                mode='lines', name=f"{ticker2}",
                line=dict(color='#FF00FF', width=2, dash='dot')
            ))

        if clip_outliers and y_limit:
            fig_vel.update_yaxes(range=[0, y_limit])

        fig_vel.update_layout(
            template="plotly_dark", 
            height=350, 
            margin=dict(l=10, r=10, t=30, b=10),
            legend=dict(orientation="h", y=1.1),
            hovermode="x unified",
            yaxis_title="Messages per Hour"
        )
        st.plotly_chart(fig_vel, use_container_width=True)

    # --- CHART 3: DAILY SENTIMENT (With Toggle) ---
    st.markdown("---")
    st.subheader(f"Daily Average Sentiment ({ticker})")
    
    # NEW: Toggle for weighting scheme
    sent_mode = st.radio(
        "Weighting Scheme", 
        ["Equal Weight (Standard)", "Crowd Weight (Upvotes)"], 
        horizontal=True,
        key="sent_mode"
    )

    # Logic to select correct metric
    if sent_mode == "Crowd Weight (Upvotes)":
        # Must use s_summary as it contains the weighted calc
        plot_df = s_summary
        y_col = 'sentiment_weighted'
        st.caption("Weighted by post score. Posts with high upvotes have more impact.")
    else:
        # Prefer granular daily aggregation if available
        plot_df = s_daily if not s_daily.empty else s_summary
        y_col = 'score' if 'score' in plot_df.columns else 'sentiment_mean'
        st.caption("Simple average of all posts. Every post counts equally.")
    
    if not plot_df.empty:
        # Safety check if column exists
        if y_col not in plot_df.columns:
            st.warning(f"Metric '{y_col}' not found. Please run your updated pipeline (reddit_sentiment_analyzer.py) to generate weighted scores.")
        else:
            fig_sent = go.Figure()
            
            # Dynamic Color Logic
            colors = ['#00FF7F' if val >= 0 else '#FF4444' for val in plot_df[y_col]]
            
            fig_sent.add_trace(go.Bar(
                x=plot_df['date'], 
                y=plot_df[y_col],
                name=f"{ticker} Sentiment",
                marker_color=colors
            ))
            
            fig_sent.add_hline(y=0, line_dash="solid", line_color="white", line_width=1)
            
            fig_sent.update_layout(
                template="plotly_dark", 
                height=350, 
                margin=dict(l=10, r=10, t=30, b=10),
                yaxis=dict(title="Score (-1 to +1)"),
                hovermode="x unified"
            )
            st.plotly_chart(fig_sent, use_container_width=True)
            
    else:
        st.info(f"No sentiment data available for {ticker} in this range.")

# ==============================================================================
# MAIN NAVIGATION
# ==============================================================================
def main():
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", ["Home", "Terminal"])
    
    if page == "Home":
        render_home()
    else:
        render_terminal()

if __name__ == "__main__":
    main()