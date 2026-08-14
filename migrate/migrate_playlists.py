import os
import sys
import sqlite3

sqlite_path = os.path.join(os.path.dirname(__file__), 'data', 'shows.db')
if not os.path.exists(sqlite_path):
    print(f"Error: SQLite file not found at {sqlite_path}")
    sys.exit(1)

conn = sqlite3.connect(sqlite_path)
cursor = conn.cursor()

# Create playlists table
cursor.execute("""
CREATE TABLE IF NOT EXISTS playlists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    show_id INTEGER NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    shot_ids TEXT,
    created_at VARCHAR(50),
    FOREIGN KEY (show_id) REFERENCES shows(id)
)
""")
print("Created 'playlists' table")

conn.commit()
conn.close()
print("Migration completed!")