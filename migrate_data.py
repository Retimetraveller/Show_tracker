import os
import sys
import sqlite3
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime

# Get Render DB URL from environment or input
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    DATABASE_URL = input("Enter your Render PostgreSQL DATABASE_URL: ")

if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

# Connect to local SQLite
sqlite_path = os.path.join(os.path.dirname(__file__), 'data', 'shows.db')
if not os.path.exists(sqlite_path):
    print(f"Error: SQLite file not found at {sqlite_path}")
    sys.exit(1)

sqlite_conn = sqlite3.connect(sqlite_path)
sqlite_conn.row_factory = sqlite3.Row

# Connect to PostgreSQL
pg_conn = psycopg2.connect(DATABASE_URL)
pg_conn.autocommit = False
pg_cursor = pg_conn.cursor()

def table_exists(table):
    pg_cursor.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = %s)", (table,))
    return pg_cursor.fetchone()[0]

def clear_table(table):
    pg_cursor.execute(f"DELETE FROM {table};")

def copy_table(table, columns, row_mapper=None):
    # Clear existing
    clear_table(table)
    # Fetch from SQLite
    rows = sqlite_conn.execute(f"SELECT * FROM {table}").fetchall()
    if not rows:
        print(f"  No rows in {table}, skipping")
        return
    # Map to dict
    data = []
    for row in rows:
        d = {k: row[k] for k in row.keys()}
        if row_mapper:
            d = row_mapper(d)
        # Convert None to empty string for text fields, keep None for ints
        for col in columns:
            if d.get(col) is None and col not in ['id', 'show_id', 'sequence_id']:
                d[col] = ''
        data.append(tuple(d.get(c) for c in columns))
    # Insert in batch
    placeholders = ','.join(['%s'] * len(columns))
    insert_sql = f"INSERT INTO {table} ({','.join(columns)}) VALUES ({placeholders})"
    execute_values(pg_cursor, insert_sql, data)
    print(f"  Copied {len(data)} rows to {table}")

# Create tables if they don't exist (they will if app has run once, but we'll ensure)
# We'll skip creation because Render will create them on first deploy.
print("Starting migration...")

# Copy in dependency order
copy_table('shows', ['id', 'name', 'client', 'producer', 'vfx_supervisor', 'comp_supervisor',
                     'start_date', 'delivery_date', 'budget', 'fps', 'resolution',
                     'colorspace', 'notes', 'status', 'created_at'])

copy_table('sequences', ['id', 'show_id', 'name', 'description', 'created_at'])

copy_table('artists', ['id', 'show_id', 'name', 'department', 'email', 'phone', 'rate', 'role', 'created_at'])

copy_table('shots', ['id', 'show_id', 'sequence_id', 'name', 'description', 'shot_type',
                     'frames', 'duration', 'status', 'priority', 'assigned_to', 'notes',
                     'created_at', 'updated_at'])

copy_table('history', ['id', 'show_id', 'action', 'timestamp'])

# Commit
pg_conn.commit()
print("Migration completed successfully!")
pg_cursor.close()
pg_conn.close()
sqlite_conn.close()