-- Reddit Posts Table
CREATE TABLE IF NOT EXISTS reddit_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id TEXT UNIQUE NOT NULL,
    symbol TEXT NOT NULL,
    title TEXT,
    text TEXT,
    score INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    timestamp_iso DATETIME,
    timestamp_raw REAL,
    subreddit TEXT,
    
    -- Sentiment Analysis Fields (populated after analysis)
    sentiment_label TEXT,
    sentiment_score REAL,
    confidence REAL,
    
    -- Metadata
    scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    sentiment_analyzed_at DATETIME
);

CREATE INDEX IF NOT EXISTS idx_reddit_symbol_time ON reddit_posts(symbol, timestamp_iso);
CREATE INDEX IF NOT EXISTS idx_reddit_post_id ON reddit_posts(post_id);
CREATE INDEX IF NOT EXISTS idx_reddit_sentiment_label ON reddit_posts(sentiment_label);

-- Scraping Metadata (tracks last post for incremental scraping)
CREATE TABLE IF NOT EXISTS scrape_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    symbol TEXT NOT NULL,
    subreddit TEXT,
    last_post_id TEXT,
    last_scraped DATETIME,
    posts_count INTEGER DEFAULT 0,
    UNIQUE(source, symbol, subreddit)
);

-- Daily Summary (aggregated sentiment per day)
CREATE TABLE IF NOT EXISTS daily_summary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    date DATE NOT NULL,
    source TEXT NOT NULL,
    posts_count INTEGER DEFAULT 0,
    avg_sentiment REAL,
    positive_count INTEGER DEFAULT 0,
    negative_count INTEGER DEFAULT 0,
    neutral_count INTEGER DEFAULT 0,
    avg_score REAL,
    UNIQUE(symbol, date, source)
);

CREATE INDEX IF NOT EXISTS idx_daily_symbol_date ON daily_summary(symbol, date);

-- StockTwits Posts Table (similar to Reddit)
CREATE TABLE IF NOT EXISTS stocktwits_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id TEXT UNIQUE NOT NULL,
    symbol TEXT NOT NULL,
    text TEXT,
    sentiment_raw TEXT,
    timestamp_iso DATETIME,
    timestamp_raw REAL,
    
    -- Our Analysis Fields
    sentiment_label TEXT,
    sentiment_score REAL,
    confidence REAL,
    
    -- Metadata
    scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    sentiment_analyzed_at DATETIME
);

CREATE INDEX IF NOT EXISTS idx_stocktwits_symbol_time ON stocktwits_posts(symbol, timestamp_iso);
CREATE INDEX IF NOT EXISTS idx_stocktwits_post_id ON stocktwits_posts(post_id);

-- Scraping Metadata for StockTwits
CREATE TABLE IF NOT EXISTS stocktwits_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT UNIQUE NOT NULL,
    last_scraped DATETIME,
    posts_count INTEGER DEFAULT 0,
    last_post_id TEXT
);
