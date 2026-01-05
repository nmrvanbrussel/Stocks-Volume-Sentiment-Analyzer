"""Quick database verification"""
import sqlite3

conn = sqlite3.connect('Database/reddit_sentiment.db')
c = conn.cursor()

print("\n✓ Database Verification")
print("=" * 50)

c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = c.fetchall()

print(f"\n✓ Tables ({len(tables)} total):")
for t in tables:
    c.execute(f"SELECT COUNT(*) FROM {t[0]}")
    count = c.fetchone()[0]
    print(f"  - {t[0]:25} ({count} rows)")

c.execute("SELECT name FROM sqlite_master WHERE type='index'")
indexes = c.fetchall()
print(f"\n✓ Indexes ({len(indexes)} total):")
for idx in indexes:
    print(f"  - {idx[0]}")

conn.close()
print("\n✓ Database ready to use!")
print("=" * 50 + "\n")
