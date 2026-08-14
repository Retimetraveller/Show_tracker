import os
import sys
import sqlite3

sqlite_path = os.path.join(os.path.dirname(__file__), 'data', 'shows.db')
if not os.path.exists(sqlite_path):
    print(f"Error: SQLite file not found at {sqlite_path}")
    sys.exit(1)

conn = sqlite3.connect(sqlite_path)
cursor = conn.cursor()

# Create tasks table
cursor.execute("""
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shot_id INTEGER REFERENCES shots(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    status VARCHAR(50) DEFAULT 'Not Started',
    assigned_to VARCHAR(200),
    notes TEXT,
    created_at VARCHAR(50),
    updated_at VARCHAR(50)
)
""")
print("Created 'tasks' table")

# Add version column to shots if missing
try:
    cursor.execute("ALTER TABLE shots ADD COLUMN version VARCHAR(20) DEFAULT 'v001'")
    print("Added 'version' column to shots")
except sqlite3.OperationalError as e:
    if "duplicate column" in str(e):
        print("Column 'version' already exists")
    else:
        print(f"Error: {e}")

conn.commit()
conn.close()
print("Migration completed!")
