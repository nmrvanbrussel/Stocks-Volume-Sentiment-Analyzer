"""
Centralized configuration for the sentiment analysis pipeline.
"""
from pathlib import Path
import os
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
env_path = PROJECT_ROOT / ".env"
load_dotenv(dotenv_path=env_path)

# Database
DATABASE_PATH = PROJECT_ROOT / "Database" / "reddit_sentiment.db"

# Reddit API Configuration
REDDIT_CONFIG = {
    'client_id': os.getenv("REDDIT_CLIENT_ID"),
    'client_secret': os.getenv("REDDIT_CLIENT_SECRET"),
    'user_agent': os.getenv("REDDIT_USER_AGENT", "wsb-ticker-scraper/0.1 by Niels van Brussel"),
    'subreddit': 'QuantFinance',
    'symbols': ['NVDA', 'AAPL', 'GOOG', 'META', 'MSFT', 'AMD', 'AMZN', 'TSLA'],
    'target_posts': 500,  # Reduced from 2000 since now incremental
    'max_pages': 20,
    'sleep_sec': 2
}

# API Server Configuration
API_CONFIG = {
    'host': '0.0.0.0',
    'port': 8000,
    'debug': False
}

# StockTwits Configuration
STOCKTWITS_CONFIG = {
    'symbols': ['AAPL', 'ACHR', 'DGXX', 'GOOG', 'IREN', 'MSAI', 'NVDA'],
    'sleep_sec': 2
}

# Sentiment Analysis Configuration
SENTIMENT_CONFIG = {
    'model_name': 'ProsusAI/finbert',
    'use_quantization': True,  # Use 8-bit quantization for RPi
    'batch_size': 8,
    'device': 'cuda' if os.getenv('USE_CUDA', 'false').lower() == 'true' else 'cpu'
}

# Data Paths
DATA_PATHS = {
    'raw': PROJECT_ROOT / 'data' / 'raw',
    'archive': PROJECT_ROOT / 'data' / 'archive',
    'processed': PROJECT_ROOT / 'data' / 'processed',
    'volume_history': PROJECT_ROOT / 'data' / 'volume_history'
}

# Ensure paths exist
for path in DATA_PATHS.values():
    path.mkdir(parents=True, exist_ok=True)
