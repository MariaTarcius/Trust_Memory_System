import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'memory.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create Memories table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS memories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject TEXT NOT NULL,
        predicate TEXT NOT NULL,
        object TEXT,
        confidence REAL NOT NULL,
        status TEXT NOT NULL,
        sources TEXT NOT NULL, -- JSON string of list
        first_seen TEXT NOT NULL,
        last_updated TEXT NOT NULL,
        corroboration_count INTEGER DEFAULT 1,
        revision_count INTEGER DEFAULT 0,
        UNIQUE(subject, predicate)
    )
    ''')
    
    # Create ChangeLog table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS changelog (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        claim_id TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        action TEXT NOT NULL,
        reason TEXT NOT NULL,
        old_value TEXT,
        new_value TEXT,
        confidence_delta REAL NOT NULL
    )
    ''')
    
    # Create Provenance table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS provenance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        memory_id INTEGER,
        timestamp TEXT NOT NULL,
        action TEXT NOT NULL,
        triggering_claim_id TEXT NOT NULL,
        confidence_before REAL NOT NULL,
        confidence_after REAL NOT NULL,
        explanation TEXT NOT NULL,
        FOREIGN KEY (memory_id) REFERENCES memories(id)
    )
    ''')
    
    conn.commit()
    conn.close()
    print("Database initialized successfully.")

if __name__ == "__main__":
    init_db()
