import os
import math
import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
from datetime import datetime


# 1) Input CSV from your scraper
CSV_PATH = r"C:\Users\nmrva\OneDrive\Desktop\Screening and Scraping\data\raw\stocktwits\2025\11\05\stocktwits_messages_ACHR_20251105_193022.csv"  # change as needed
TEXT_COL = "message"
SYMBOL_COL = "symbol"

# 2) Load data
df = pd.read_csv(CSV_PATH)
df[TEXT_COL] = df[TEXT_COL].astype(str).fillna("")

# 3) FinBERT pipeline
MODEL_ID = "ProsusAI/finbert"
DEVICE = 0 if torch.cuda.is_available() else -1
tok = AutoTokenizer.from_pretrained(MODEL_ID)
clf = AutoModelForSequenceClassification.from_pretrained(MODEL_ID)
pipe = pipeline("text-classification", model = clf, tokenizer = tok, return_all_scores = True, truncation = True, device = DEVICE)

# pk ​= eℓpos ​+ eℓneu ​+ eℓneg​eℓk​​,k ∈ {pos, neu, neg}, softmax function to get probabilities

#This would come out of pipe(text) 

#[
#  {"label": "positive", "score": 0.72},
#  {"label": "neutral",  "score": 0.20},
#  {"label": "negative", "score": 0.08}
#]

# 4) Run in batches for stability
def infer_batch(texts, batch_size = 64): #Breaks the list of messages into chunks with batch sizes 64
    print("Creating Chunks")
    out = [] 
    for i in range(0, len(texts), batch_size): #range(0, N, b)
        out.extend(pipe(texts[i:i+batch_size])) #seq[start:stop]
        #[0,b), [b,2b), …, [kb,min((k+1)b,N))
    return out

scores = infer_batch(df[TEXT_COL].tolist())

#We cannot use append here as this would create a nested list 

# 5) Convert scores to numeric columns
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

summary = res.groupby(SYMBOL_COL, dropna=False).apply(summarize).reset_index()

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ts = datetime.now().strftime("%Y%m%d_%H%M%S")

# Write per-message outputs to data/processed/finbert/YYYY/MM/DD/
today = datetime.utcnow()
processed_dir = os.path.join(project_root, 'data', 'processed', 'finbert', f"{today:%Y}", f"{today:%m}", f"{today:%d}")
os.makedirs(processed_dir, exist_ok=True)
enriched_out = os.path.join(
    processed_dir,
    f"{os.path.splitext(os.path.basename(CSV_PATH))[0]}_with_finbert.csv"
)

# Write summary to reports/YYYY/MM/DD/
reports_dir = os.path.join(project_root, 'reports', f"{today:%Y}", f"{today:%m}", f"{today:%d}")
os.makedirs(reports_dir, exist_ok=True)
summary_out = os.path.join(
    reports_dir,
    f"summary_finbert_{ts}.csv"
)

res.to_csv(enriched_out, index=False, encoding="utf-8")
summary.to_csv(summary_out, index=False, encoding="utf-8")

print(f"Saved per-message results: {enriched_out}")
print(f"Saved summary: {summary_out}")
print(summary)