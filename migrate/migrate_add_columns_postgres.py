import os
import sys
import psycopg2
from psycopg2.extras import execute_values

# Get connection string
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    DATABASE_URL = input("Enter your Neon PostgreSQL DATABASE_URL: ")

if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

try:
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cursor = conn.cursor()
    print("Connected to database.")

    # Add columns to shows table
    try:
        cursor.execute("ALTER TABLE shows ADD COLUMN thumbnail TEXT;")
        print("Added column 'thumbnail' to shows table.")
    except psycopg2.errors.DuplicateColumn:
        print("Column 'thumbnail' already exists, skipping.")
    except Exception as e:
        print(f"Error adding thumbnail: {e}")

    # Add columns to shots table
    columns = [
        ("client_status", "VARCHAR(50) DEFAULT 'Not Sent'"),
        ("client_notes", "TEXT"),
        ("client_sent_date", "VARCHAR(50)"),
        ("client_approved_date", "VARCHAR(50)"),
        ("department", "VARCHAR(50)")
    ]
    for col_name, col_type in columns:
        try:
            cursor.execute(f"ALTER TABLE shots ADD COLUMN {col_name} {col_type};")
            print(f"Added column '{col_name}' to shots table.")
        except psycopg2.errors.DuplicateColumn:
            print(f"Column '{col_name}' already exists, skipping.")
        except Exception as e:
            print(f"Error adding {col_name}: {e}")

    cursor.close()
    conn.close()
    print("Migration completed successfully!")

except Exception as e:
    print(f"Connection error: {e}")
    sys.exit(1)