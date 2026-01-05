"""
FastAPI server for sentiment analysis data.
Serves sentiment data, volume statistics, and other metrics.

Usage:
    uvicorn API.api_server:app --reload --host 0.0.0.0 --port 8000
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import DATABASE_PATH, API_CONFIG
from Database.db_utils import DatabaseManager

app = FastAPI(
    title="Stock Sentiment API",
    description="API for accessing Reddit and StockTwits sentiment analysis",
    version="1.0.0"
)

db_manager = DatabaseManager(DATABASE_PATH)


@app.get("/")
async def root():
    """API health check."""
    return {
        "status": "online",
        "service": "Stock Sentiment Analysis API",
        "version": "1.0.0",
        "endpoints": {
            "sentiment": "/api/v1/sentiment/{symbol}",
            "volume": "/api/v1/volume/{symbol}",
            "summary": "/api/v1/summary/{symbol}",
            "health": "/health"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/api/v1/sentiment/{symbol}")
async def get_sentiment(
    symbol: str,
    days: int = Query(7, ge=1, le=90),
    source: str = Query("reddit", regex="^(reddit|stocktwits)$")
):
    """
    Get sentiment summary for a symbol.
    
    Args:
        symbol: Stock ticker (e.g., AAPL, NVDA)
        days: Number of days to look back (default: 7, max: 90)
        source: Data source (reddit or stocktwits)
    
    Returns:
        Sentiment counts and averages
    """
    try:
        summary = db_manager.get_sentiment_summary(symbol.upper(), days=days, source=source)
        
        if not summary:
            raise HTTPException(status_code=404, detail=f"No data found for {symbol}")
        
        total_posts = sum(s['count'] for s in summary.values())
        
        return {
            "symbol": symbol.upper(),
            "source": source,
            "days": days,
            "total_posts": total_posts,
            "sentiment": {
                "positive": {
                    "count": summary.get("positive", {}).get("count", 0),
                    "avg_score": summary.get("positive", {}).get("avg_score", 0)
                },
                "negative": {
                    "count": summary.get("negative", {}).get("count", 0),
                    "avg_score": summary.get("negative", {}).get("avg_score", 0)
                },
                "neutral": {
                    "count": summary.get("neutral", {}).get("count", 0),
                    "avg_score": summary.get("neutral", {}).get("avg_score", 0)
                }
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/volume/{symbol}")
async def get_volume(
    symbol: str,
    hours: int = Query(24, ge=1, le=720)
):
    """
    Get posting volume statistics.
    
    Args:
        symbol: Stock ticker
        hours: Number of hours to look back
    
    Returns:
        Volume statistics and hourly breakdown
    """
    try:
        stats = db_manager.get_volume_stats(symbol.upper(), hours=hours)
        
        if stats['total_posts'] == 0:
            raise HTTPException(status_code=404, detail=f"No posts found for {symbol}")
        
        return {
            "symbol": symbol.upper(),
            "hours": hours,
            "total_posts": stats['total_posts'],
            "posts_per_hour": round(stats['posts_per_hour'], 2),
            "hourly_breakdown": stats['hourly_breakdown'],
            "timestamp": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/summary/{symbol}")
async def get_summary(
    symbol: str,
    days: int = Query(7, ge=1, le=90)
):
    """
    Get comprehensive summary (sentiment + volume).
    
    Args:
        symbol: Stock ticker
        days: Number of days to look back
    
    Returns:
        Combined sentiment and volume data
    """
    try:
        symbol_upper = symbol.upper()
        
        # Get Reddit data
        reddit_sentiment = db_manager.get_sentiment_summary(symbol_upper, days=days, source='reddit')
        reddit_volume = db_manager.get_volume_stats(symbol_upper, hours=days*24, source='reddit')
        
        # Get StockTwits data
        try:
            stocktwits_sentiment = db_manager.get_sentiment_summary(symbol_upper, days=days, source='stocktwits')
            stocktwits_volume = db_manager.get_volume_stats(symbol_upper, hours=days*24, source='stocktwits')
        except:
            stocktwits_sentiment = {}
            stocktwits_volume = {"total_posts": 0, "posts_per_hour": 0}
        
        if not reddit_sentiment and not stocktwits_sentiment:
            raise HTTPException(status_code=404, detail=f"No data found for {symbol}")
        
        return {
            "symbol": symbol_upper,
            "days": days,
            "reddit": {
                "sentiment": reddit_sentiment,
                "volume": {
                    "total_posts": reddit_volume['total_posts'],
                    "posts_per_hour": round(reddit_volume['posts_per_hour'], 2)
                }
            },
            "stocktwits": {
                "sentiment": stocktwits_sentiment,
                "volume": {
                    "total_posts": stocktwits_volume['total_posts'],
                    "posts_per_hour": round(stocktwits_volume['posts_per_hour'], 2)
                }
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/symbols")
async def get_symbols():
    """Get list of tracked symbols."""
    from config import REDDIT_CONFIG, STOCKTWITS_CONFIG
    
    return {
        "reddit": REDDIT_CONFIG['symbols'],
        "stocktwits": STOCKTWITS_CONFIG['symbols'],
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=API_CONFIG['host'],
        port=API_CONFIG['port'],
        log_level="info"
    )
