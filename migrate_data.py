import os
import sys
import sqlite3
import psycopg2
from psycopg2.extras import execute_values

# ==================== SAFETY CHECK ====================
print("=" * 60)
print("This script will COPY data from your local SQLite to Neon.")
print("It assumes the tables are already empty or have no conflicting data.")
print("=" * 60)
confirm = input("Type 'yes' to continue: ")
if confirm.lower() != 'yes':
    print("Aborted.")
    sys.exit(0)
# ======================================================

DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    DATABASE_URL = input("Enter your Render PostgreSQL DATABASE_URL: ")

if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

sqlite_path = os.path.join(os.path.dirname(__file__), 'data', 'shows.db')
if not os.path.exists(sqlite_path):
    print(f"Error: SQLite file not found at {sqlite_path}")
    sys.exit(1)

sqlite_conn = sqlite3.connect(sqlite_path)
sqlite_conn.row_factory = sqlite3.Row

pg_conn = psycopg2.connect(DATABASE_URL)
pg_conn.autocommit = False
pg_cursor = pg_conn.cursor()

def copy_table(table, columns, row_mapper=None):
    rows = sqlite_conn.execute(f"SELECT * FROM {table}").fetchall()
    if not rows:
        print(f"  No rows in {table}, skipping")
        return
    data = []
    for row in rows:
        d = {k: row[k] for k in row.keys()}
        if row_mapper:
            d = row_mapper(d)
        for col in columns:
            if d.get(col) is None and col not in ['id', 'show_id', 'sequence_id']:
                d[col] = ''
        data.append(tuple(d.get(c) for c in columns))
    placeholders = ','.join(['%s'] * len(columns))
    insert_sql = f"INSERT INTO {table} ({','.join(columns)}) VALUES %s"
    execute_values(pg_cursor, insert_sql, data)
    print(f"  Copied {len(data)} rows to {table}")

print("Starting migration (copy only, no clearing)...")

# Copy in dependency order (parent tables first)
copy_table('shows', ['id', 'name', 'client', 'producer', 'vfx_supervisor', 'comp_supervisor',
                     'start_date', 'delivery_date', 'budget', 'fps', 'resolution',
                     'colorspace', 'notes', 'status', 'created_at'])

copy_table('sequences', ['id', 'show_id', 'name', 'description', 'created_at'])

copy_table('artists', ['id', 'show_id', 'name', 'department', 'email', 'phone', 'rate', 'role', 'created_at'])

copy_table('shots', ['id', 'show_id', 'sequence_id', 'name', 'description', 'shot_type',
                     'frames', 'duration', 'status', 'priority', 'assigned_to', 'notes',
                     'created_at', 'updated_at'])

copy_table('history', ['id', 'show_id', 'action', 'timestamp'])

pg_conn.commit()
print("Migration completed successfully!")
pg_cursor.close()
pg_conn.close()
sqlite_conn.close()