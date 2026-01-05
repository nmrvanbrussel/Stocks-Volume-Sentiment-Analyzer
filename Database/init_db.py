"""
Database initialization script.
Run this once to create the database schema.
"""
import sqlite3
from pathlib import Path
import sys

def init_database(db_path: Path) -> None:
    """Create database and initialize schema."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Read and execute schema
    schema_file = db_path.parent / 'schema.sql'
    if not schema_file.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_file}")
    
    with open(schema_file, 'r') as f:
        schema = f.read()
    
    # Execute schema (handles multiple statements)
    cursor.executescript(schema)
    conn.commit()
    conn.close()
    
    print(f"✓ Database initialized at {db_path}")

if __name__ == "__main__":
    # Add parent directory to path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from config import DATABASE_PATH
    try:
        init_database(DATABASE_PATH)
    except Exception as e:
        print(f"✗ Error initializing database: {e}", file=sys.stderr)
        sys.exit(1)
