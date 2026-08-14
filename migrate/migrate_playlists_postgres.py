import os
import sys
import psycopg2

# Get connection string
DATABASE_URL = input("Enter your Neon PostgreSQL DATABASE_URL: ")

if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

try:
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cursor = conn.cursor()
    print("Connected to database.")

    # Create playlists table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS playlists (
            id SERIAL PRIMARY KEY,
            show_id INTEGER NOT NULL REFERENCES shows(id),
            name VARCHAR(200) NOT NULL,
            description TEXT,
            shot_ids TEXT,
            created_at VARCHAR(50)
        )
    """)
    print("Created 'playlists' table in PostgreSQL")

    cursor.close()
    conn.close()
    print("Migration completed successfully!")

except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
