import os
import sys
import sqlite3
import psycopg2
from psycopg2.extras import execute_values

# Get Neon connection string
DATABASE_URL = input("Enter your Neon PostgreSQL DATABASE_URL: ")
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

# Build correct path: project_root/data/shows.db
# __file__ is inside migrate/, so go up one level to project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sqlite_path = os.path.join(project_root, 'data', 'shows.db')

if not os.path.exists(sqlite_path):
    print(f"Creating new database at {sqlite_path}")
    os.makedirs(os.path.dirname(sqlite_path), exist_ok=True)
    import sqlite3
    conn = sqlite3.connect(sqlite_path)
    conn.close()

sqlite_conn = sqlite3.connect(sqlite_path)
sqlite_cursor = sqlite_conn.cursor()

# Clear local tables in correct order (child first)
tables = ['history', 'shots', 'sequences', 'artists', 'shows']
for table in tables:
    sqlite_cursor.execute(f"DELETE FROM {table}")
    print(f"Cleared local {table}")

# Connect to Neon
pg_conn = psycopg2.connect(DATABASE_URL)
pg_cursor = pg_conn.cursor()

def copy_table(table, columns):
    pg_cursor.execute(f"SELECT {','.join(columns)} FROM {table}")
    rows = pg_cursor.fetchall()
    if not rows:
        print(f"  No rows in {table}, skipping")
        return
    placeholders = ','.join(['?'] * len(columns))
    insert_sql = f"INSERT INTO {table} ({','.join(columns)}) VALUES ({placeholders})"
    sqlite_cursor.executemany(insert_sql, rows)
    print(f"  Copied {len(rows)} rows to local {table}")

# Copy in dependency order (parent first)
copy_table('shows', ['id', 'name', 'client', 'producer', 'vfx_supervisor', 'comp_supervisor',
                     'start_date', 'delivery_date', 'budget', 'fps', 'resolution',
                     'colorspace', 'notes', 'status', 'created_at', 'thumbnail'])

copy_table('sequences', ['id', 'show_id', 'name', 'description', 'created_at'])

copy_table('artists', ['id', 'show_id', 'name', 'department', 'email', 'phone', 'rate', 'role', 'created_at'])

copy_table('shots', ['id', 'show_id', 'sequence_id', 'name', 'description', 'shot_type',
                     'frames', 'duration', 'status', 'priority', 'assigned_to', 'notes',
                     'created_at', 'updated_at', 'client_status', 'client_notes',
                     'client_sent_date', 'client_approved_date', 'department', 'thumbnail', 'version',
                     'bid_days', 'used_days', 'deadline'])

copy_table('history', ['id', 'show_id', 'action', 'timestamp'])

sqlite_conn.commit()
pg_cursor.close()
pg_conn.close()
sqlite_conn.close()

print("✅ Local SQLite now matches Neon data.")