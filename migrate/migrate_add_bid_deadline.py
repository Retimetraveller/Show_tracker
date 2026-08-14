import os
import sys
import sqlite3

sqlite_path = os.path.join(os.path.dirname(__file__), 'data', 'shows.db')
if not os.path.exists(sqlite_path):
    print(f"Error: SQLite file not found at {sqlite_path}")
    sys.exit(1)

conn = sqlite3.connect(sqlite_path)
cursor = conn.cursor()

# Add columns to shots table
columns = [
    ("bid_days", "INTEGER DEFAULT 0"),
    ("used_days", "INTEGER DEFAULT 0"),
    ("deadline", "VARCHAR(50)")
]

for col_name, col_type in columns:
    try:
        cursor.execute(f"ALTER TABLE shots ADD COLUMN {col_name} {col_type}")
        print(f"Added column '{col_name}' to shots table")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print(f"Column '{col_name}' already exists, skipping")
        else:
            print(f"Error adding column '{col_name}': {e}")

conn.commit()
conn.close()
print("Migration completed!")