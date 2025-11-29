import os
import math
import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
from datetime import datetime

# ============================================================================
# STEP 1: Imports and Setup
# ============================================================================
# Same imports as stockwits_sentiment_analyzer.py
# We need pandas for data manipulation, torch for GPU, transformers for FinBERT

# ============================================================================
# STEP 2: CSV Path Configuration
# ============================================================================
# Input CSV from Reddit scraper
CSV_PATH = r"C:\Users\nmrva\OneDrive\Desktop\Screening and Scraping\data\raw\reddit\GOOG\2025\11\29\reddit_posts_GOOG_20251129_212349.csv"  # change as needed

# For Reddit, we'll combine title + text for better sentiment analysis
# TEXT_COL will be created from combining 'title' and 'text' columns
SYMBOL_COL = "symbol"

# ============================================================================
# STEP 3: Data Loading and Preparation
# ============================================================================
# Load data
df = pd.read_csv(CSV_PATH)

# Combine title and text for better sentiment analysis
# Reddit posts have both title and text, combining gives more context
df['title'] = df['title'].fillna('').astype(str)
df['text'] = df['text'].fillna('').astype(str)
df['combined_text'] = df['title'] + ' ' + df['text']
df['combined_text'] = df['combined_text'].astype(str).fillna("")

# Use combined_text as our TEXT_COL for sentiment analysis
TEXT_COL = "combined_text"

# ============================================================================
# STEP 4: FinBERT Model Setup
# ============================================================================
# Same FinBERT model as stockwits analyzer
MODEL_ID = "ProsusAI/finbert"
DEVICE = 0 if torch.cuda.is_available() else -1
tok = AutoTokenizer.from_pretrained(MODEL_ID)
clf = AutoModelForSequenceClassification.from_pretrained(MODEL_ID)
pipe = pipeline("text-classification", model = clf, tokenizer = tok, top_k = None, truncation = True, device = DEVICE)

# pk = eℓpos + eℓneu + eℓneg​eℓk​​,k ∈ {pos, neu, neg}, softmax function to get probabilities

#This would come out of pipe(text) 

#[
#  {"label": "positive", "score": 0.72},
#  {"label": "neutral",  "score": 0.20},
#  {"label": "negative", "score": 0.08}
#]

# ============================================================================
# STEP 5: Batch Inference
# ============================================================================
# Run in batches for stability - same function as stockwits
def infer_batch(texts, batch_size = 64): #Breaks the list of messages into chunks with batch sizes 64
    print("Creating Chunks")
    out = [] 
    for i in range(0, len(texts), batch_size): #range(0, N, b)
        out.extend(pipe(texts[i:i+batch_size])) #seq[start:stop]
        #[0,b), [b,2b), …, [kb,min((k+1)b,N))
    return out

# Run inference on combined text column
scores = infer_batch(df[TEXT_COL].tolist())

#We cannot use append here as this would create a nested list 

# ============================================================================
# STEP 6: Convert Scores to DataFrame
# ============================================================================
# Convert scores to numeric columns - same function as stockwits
def to_row(score_list):
    m = {d["label"].lower(): d["score"] for d in score_list}
    pred_label = max(m, key = m.get) #argmax over the label scores 
    conf = m[pred_label] #confidence score for the predicted label
    signed = m["positive"] - m["negative"] #signed score of the predicted label
    # y = argmax{p_pos, p_neu, p_neg}
    # c = max{p_pos, p_neu, p_neg}
    # s = p_pos - p_neg ∈ [-1, 1]
    return pd.Series({
        "prob_positive": m["positive"],
        "prob_negative": m["negative"],
        "prob_neutral":  m["neutral"],
        "pred_label":    pred_label,
        "confidence":    conf,
        "sentiment_signed": signed
    })

probs_df = pd.DataFrame([to_row(s) for s in scores])
res = pd.concat([df.reset_index(drop=True), probs_df], axis=1)

#Each message would produce a list like:
#[
#  {"label":"positive","score":p_pos},
#  {"label":"neutral", "score":p_neu},
#  {"label":"negative","score":p_neg}
#]

# ============================================================================
# STEP 7: Summarization
# ============================================================================
# Summarize by symbol - same function as stockwits
def summarize(group):
    print("Summarizing")
    n = len(group)
    pos_share = (group["pred_label"] == "positive").mean()
    neg_share = (group["pred_label"] == "negative").mean()
    neu_share = (group["pred_label"] == "neutral").mean()

    pos_mean = group["prob_positive"].mean()
    neg_mean = group["prob_negative"].mean()
    neu_mean = group["prob_neutral"].mean()

    sentiment_total = group["sentiment_signed"].sum()
    sentiment_mean  = group["sentiment_signed"].mean()
    conf_mean = group["confidence"].mean()

    return pd.Series({
        "messages": n,
        "pos_share": round(pos_share, 4),
        "neg_share": round(neg_share, 4),
        "neu_share": round(neu_share, 4),
        "prob_pos_mean": round(pos_mean, 4),
        "prob_neg_mean": round(neg_mean, 4),
        "prob_neu_mean": round(neu_mean, 4),
        "sentiment_mean": round(sentiment_mean, 4),
        "sentiment_total": round(sentiment_total, 4),
        "confidence_mean": round(conf_mean, 4),
    })

summary = res.groupby(SYMBOL_COL, dropna=False).apply(summarize, include_groups = False).reset_index()

# ============================================================================
# STEP 8: File Output Paths
# ============================================================================
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ts = datetime.now().strftime("%Y%m%d_%H%M%S")

ticker_val = str(df[SYMBOL_COL].iloc[0].strip().upper())

# Write per-message outputs to data/processed/finbert/reddit/{SYMBOL}/{YEAR}/{MONTH}/{DAY}/
today = datetime.utcnow()
processed_dir = os.path.join(project_root, 'data', 'processed', 'finbert', 'reddit', f"{ticker_val}", f"{today:%Y}", f"{today:%m}", f"{today:%d}")
os.makedirs(processed_dir, exist_ok=True)
enriched_out = os.path.join(
    processed_dir,
    f"{os.path.splitext(os.path.basename(CSV_PATH))[0]}_with_finbert.csv"
)

# Write summary to reports/reddit/{SYMBOL}/{YEAR}/{MONTH}/{DAY}/
reports_dir = os.path.join(project_root, 'reports', 'reddit', f"{ticker_val}", f"{today:%Y}", f"{today:%m}", f"{today:%d}")
os.makedirs(reports_dir, exist_ok=True)
summary_out = os.path.join(
    reports_dir,
    f"summary_reddit_finbert_{ts}.csv"
)

# ============================================================================
# STEP 9: Save Files
# ============================================================================
res.to_csv(enriched_out, index=False, encoding="utf-8")
summary.to_csv(summary_out, index=False, encoding="utf-8")

print(f"Saved per-message results: {enriched_out}")
print(f"Saved summary: {summary_out}")
print(summary)

