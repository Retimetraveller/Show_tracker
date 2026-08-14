import os
import sys
import psycopg2

DATABASE_URL = input("Enter your Neon PostgreSQL DATABASE_URL: ")
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

try:
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cursor = conn.cursor()
    print("Connected to database.")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
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
    except Exception as e:
        if "duplicate column" in str(e).lower():
            print("Column 'version' already exists")
        else:
            print(f"Warning: {e}")

    cursor.close()
    conn.close()
    print("Migration completed successfully!")

except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)