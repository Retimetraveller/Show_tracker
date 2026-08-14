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
    ("client_status", "TEXT DEFAULT 'Not Sent'"),
    ("client_notes", "TEXT"),
    ("client_sent_date", "TEXT"),
    ("client_approved_date", "TEXT"),
    ("department", "TEXT"),
    ("thumbnail", "TEXT"),
    ("tasks", "TEXT")
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

# Add column to shows table
try:
    cursor.execute("ALTER TABLE shows ADD COLUMN thumbnail TEXT")
    print("Added column 'thumbnail' to shows table")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("Column 'thumbnail' already exists, skipping")
    else:
        print(f"Error adding column 'thumbnail': {e}")

conn.commit()
conn.close()
print("Local SQLite migration completed!")