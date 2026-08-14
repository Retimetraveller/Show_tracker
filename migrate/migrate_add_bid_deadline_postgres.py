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

    columns = [
        ("bid_days", "INTEGER DEFAULT 0"),
        ("used_days", "INTEGER DEFAULT 0"),
        ("deadline", "VARCHAR(50)")
    ]

    for col_name, col_type in columns:
        try:
            cursor.execute(f"ALTER TABLE shots ADD COLUMN IF NOT EXISTS {col_name} {col_type}")
            print(f"Added column '{col_name}' to shots table")
        except Exception as e:
            print(f"Error adding column '{col_name}': {e}")

    cursor.close()
    conn.close()
    print("Migration completed successfully!")

except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)