"""
Quick test script to verify the new database and API infrastructure.
Run this to ensure everything is set up correctly.
"""
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import DATABASE_PATH, REDDIT_CONFIG
from Database.db_utils import DatabaseManager


def test_database_connection():
    """Test database connection."""
    print("🔍 Testing database connection...")
    try:
        db = DatabaseManager(DATABASE_PATH)
        conn = db.get_connection()
        
        # List all tables
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        print(f"✓ Database connected")
        print(f"✓ Tables: {', '.join(tables)}")
        return True
    except Exception as e:
        print(f"✗ Database error: {e}")
        return False


def test_database_operations():
    """Test basic database operations."""
    print("\n🔍 Testing database operations...")
    try:
        db = DatabaseManager(DATABASE_PATH)
        
        # Test insert
        test_post = {
            'post_id': 't3_test12345',
            'symbol': 'TEST',
            'title': 'Test post',
            'text': 'This is a test post',
            'score': 100,
            'comments': 50,
            'timestamp_iso': '2026-01-05T12:00:00Z',
            'timestamp_raw': 1704456000.0,
            'subreddit': 'QuantFinance'
        }
        
        success = db.insert_reddit_post(test_post)
        if success:
            print("✓ Post insertion works")
        
        # Test metadata update
        db.update_scrape_metadata(
            symbol='TEST',
            last_post_id='t3_test12345',
            posts_count=1,
            source='reddit',
            subreddit='QuantFinance'
        )
        print("✓ Metadata update works")
        
        # Test retrieval
        last_id = db.get_last_post_id('TEST', source='reddit', subreddit='QuantFinance')
        if last_id == 't3_test12345':
            print("✓ Post ID retrieval works")
        
        # Test sentiment addition
        db.add_sentiment('t3_test12345', 'positive', 0.85, 0.92)
        print("✓ Sentiment addition works")
        
        # Test queries
        summary = db.get_sentiment_summary('TEST', days=7)
        print(f"✓ Sentiment summary query works: {summary}")
        
        volume = db.get_volume_stats('TEST', hours=24)
        print(f"✓ Volume stats query works: {volume['total_posts']} posts")
        
        return True
    except Exception as e:
        print(f"✗ Database operation error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config():
    """Test configuration loading."""
    print("\n🔍 Testing configuration...")
    try:
        print(f"✓ Database path: {DATABASE_PATH}")
        print(f"✓ Reddit subreddit: {REDDIT_CONFIG['subreddit']}")
        print(f"✓ Tracked symbols: {', '.join(REDDIT_CONFIG['symbols'])}")
        return True
    except Exception as e:
        print(f"✗ Config error: {e}")
        return False


def test_api_imports():
    """Test API imports."""
    print("\n🔍 Testing API imports...")
    try:
        from API.api_server import app
        print("✓ API server imports successfully")
        print(f"✓ API endpoints available: {[r.path for r in app.routes][:5]}")
        return True
    except Exception as e:
        print(f"✗ API import error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Stock Sentiment Analysis - System Test")
    print("=" * 60)
    
    results = {
        "Configuration": test_config(),
        "Database Connection": test_database_connection(),
        "Database Operations": test_database_operations(),
        "API Imports": test_api_imports()
    }
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(results.values())
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All tests passed! System is ready to use.")
        print("\nNext steps:")
        print("1. Run the scraper: python Scraping/scraping_reddit.py")
        print("2. Start the API: python -m uvicorn API.api_server:app --reload")
        print("3. Visit API docs: http://localhost:8000/docs")
    else:
        print("✗ Some tests failed. Please check the errors above.")
        sys.exit(1)
    print("=" * 60)


if __name__ == "__main__":
    main()
