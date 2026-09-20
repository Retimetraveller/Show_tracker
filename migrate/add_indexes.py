"""
Adds the performance indexes introduced in this fix pass to an EXISTING
database (SQLite or Postgres/Neon). db.create_all() only creates missing
tables -- it does not alter columns or add indexes to tables that already
exist, so this script does it explicitly and is safe to run more than once
(IF NOT EXISTS).

Usage:
    python migrate/add_indexes.py
It will prompt for a DATABASE_URL, or reads it from the environment if set.
"""
import os
import sys

DATABASE_URL = os.environ.get('DATABASE_URL') or input(
    "Enter DATABASE_URL (Postgres/Neon), or leave blank to target the local "
    "SQLite file at data/shows.db: "
).strip()

INDEXES = [
    ("ix_shots_show_id", "shots", "show_id"),
    ("ix_shots_sequence_id", "shots", "sequence_id"),
    ("ix_shots_status", "shots", "status"),
    ("ix_shots_assigned_to", "shots", "assigned_to"),
    ("ix_shots_client_status", "shots", "client_status"),
    ("ix_tasks_shot_id", "tasks", "shot_id"),
    ("ix_sequences_show_id", "sequences", "show_id"),
    ("ix_artists_show_id", "artists", "show_id"),
    ("ix_playlists_show_id", "playlists", "show_id"),
    ("ix_history_show_id", "history", "show_id"),
]

if DATABASE_URL:
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    import psycopg2
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()
    for name, table, col in INDEXES:
        print(f"Creating index {name} on {table}({col}) if missing...")
        cur.execute(f'CREATE INDEX IF NOT EXISTS {name} ON {table} ({col});')
    cur.close()
    conn.close()
    print("Done. Indexes added to Postgres/Neon database.")
else:
    import sqlite3
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sqlite_path = os.path.join(project_root, 'data', 'shows.db')
    if not os.path.exists(sqlite_path):
        print(f"No SQLite database found at {sqlite_path}; nothing to do.")
        sys.exit(0)
    conn = sqlite3.connect(sqlite_path)
    cur = conn.cursor()
    for name, table, col in INDEXES:
        print(f"Creating index {name} on {table}({col}) if missing...")
        cur.execute(f'CREATE INDEX IF NOT EXISTS {name} ON {table} ({col});')
    conn.commit()
    conn.close()
    print("Done. Indexes added to local SQLite database.")
