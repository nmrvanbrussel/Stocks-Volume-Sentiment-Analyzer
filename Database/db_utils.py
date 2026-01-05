"""
Database utility functions for common operations.
"""
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any

class DatabaseManager:
    """Manager for database operations."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
    
    def get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn
    
    def insert_reddit_post(self, post_data: Dict[str, Any]) -> bool:
        """Insert or update Reddit post."""
        conn = self.get_connection()
        try:
            conn.execute("""
                INSERT OR REPLACE INTO reddit_posts 
                (post_id, symbol, title, text, score, comments, 
                 timestamp_iso, timestamp_raw, subreddit)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                post_data.get('post_id'),
                post_data.get('symbol'),
                post_data.get('title'),
                post_data.get('text'),
                post_data.get('score', 0),
                post_data.get('comments', 0),
                post_data.get('timestamp_iso'),
                post_data.get('timestamp_raw'),
                post_data.get('subreddit')
            ))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error inserting Reddit post: {e}")
            return False
        finally:
            conn.close()
    
    def insert_reddit_posts_batch(self, posts: List[Dict[str, Any]]) -> int:
        """Batch insert Reddit posts."""
        conn = self.get_connection()
        try:
            for post in posts:
                conn.execute("""
                    INSERT OR REPLACE INTO reddit_posts 
                    (post_id, symbol, title, text, score, comments, 
                     timestamp_iso, timestamp_raw, subreddit)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    post.get('post_id'),
                    post.get('symbol'),
                    post.get('title'),
                    post.get('text'),
                    post.get('score', 0),
                    post.get('comments', 0),
                    post.get('timestamp_iso'),
                    post.get('timestamp_raw'),
                    post.get('subreddit')
                ))
            conn.commit()
            return len(posts)
        except Exception as e:
            print(f"Error batch inserting Reddit posts: {e}")
            return 0
        finally:
            conn.close()
    
    def get_last_post_id(self, symbol: str, source: str = 'reddit', subreddit: str = None) -> Optional[str]:
        """Get last scraped post ID for incremental scraping."""
        conn = self.get_connection()
        try:
            cursor = conn.execute(
                "SELECT last_post_id FROM scrape_metadata WHERE source = ? AND symbol = ?",
                (source, symbol)
            )
            row = cursor.fetchone()
            return row[0] if row else None
        finally:
            conn.close()
    
    def update_scrape_metadata(self, symbol: str, last_post_id: str, posts_count: int, 
                               source: str = 'reddit', subreddit: str = None) -> bool:
        """Update scraping metadata for incremental tracking."""
        conn = self.get_connection()
        try:
            conn.execute("""
                INSERT OR REPLACE INTO scrape_metadata 
                (source, symbol, subreddit, last_post_id, last_scraped, posts_count)
                VALUES (?, ?, ?, ?, datetime('now'), ?)
            """, (source, symbol, subreddit, last_post_id, posts_count))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error updating scrape metadata: {e}")
            return False
        finally:
            conn.close()
    
    def add_sentiment(self, post_id: str, sentiment_label: str, sentiment_score: float, 
                      confidence: float, table: str = 'reddit_posts') -> bool:
        """Add sentiment analysis to a post."""
        conn = self.get_connection()
        try:
            conn.execute(f"""
                UPDATE {table}
                SET sentiment_label = ?, sentiment_score = ?, confidence = ?, 
                    sentiment_analyzed_at = datetime('now')
                WHERE post_id = ?
            """, (sentiment_label, sentiment_score, confidence, post_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error adding sentiment: {e}")
            return False
        finally:
            conn.close()
    
    def get_unanalyzed_posts(self, symbol: Optional[str] = None, limit: int = 100, 
                             table: str = 'reddit_posts') -> List[Dict]:
        """Get posts that haven't been analyzed yet."""
        conn = self.get_connection()
        try:
            query = f"SELECT * FROM {table} WHERE sentiment_label IS NULL"
            params = []
            
            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)
            
            query += " LIMIT ?"
            params.append(limit)
            
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def get_sentiment_summary(self, symbol: str, days: int = 7, source: str = 'reddit') -> Dict:
        """Get sentiment summary for a symbol in the last N days."""
        conn = self.get_connection()
        try:
            table = 'reddit_posts' if source == 'reddit' else 'stocktwits_posts'
            cursor = conn.execute(f"""
                SELECT sentiment_label, COUNT(*) as count, AVG(sentiment_score) as avg_score
                FROM {table}
                WHERE symbol = ? AND timestamp_iso > datetime('now', '-' || ? || ' days')
                GROUP BY sentiment_label
            """, (symbol, days))
            
            results = {}
            for row in cursor.fetchall():
                results[row['sentiment_label']] = {
                    'count': row['count'],
                    'avg_score': row['avg_score']
                }
            
            return results
        finally:
            conn.close()
    
    def get_volume_stats(self, symbol: str, hours: int = 24, source: str = 'reddit') -> Dict:
        """Get posting volume statistics."""
        conn = self.get_connection()
        try:
            table = 'reddit_posts' if source == 'reddit' else 'stocktwits_posts'
            cursor = conn.execute(f"""
                SELECT COUNT(*) as total, 
                       datetime(timestamp_iso) as time_bucket
                FROM {table}
                WHERE symbol = ? AND timestamp_iso > datetime('now', '-' || ? || ' hours')
                GROUP BY date(timestamp_iso), strftime('%H', timestamp_iso)
                ORDER BY time_bucket DESC
            """, (symbol, hours))
            
            rows = cursor.fetchall()
            return {
                'total_posts': sum(row['total'] for row in rows),
                'posts_per_hour': sum(row['total'] for row in rows) / hours if rows else 0,
                'hourly_breakdown': [dict(row) for row in rows]
            }
        finally:
            conn.close()

def get_db_manager(db_path: Path) -> DatabaseManager:
    """Factory function to get database manager."""
    return DatabaseManager(db_path)
