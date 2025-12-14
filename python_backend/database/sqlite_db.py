"""
SQLite Database Layer

Local cache database for fast, offline operations.

For beginners:
- SQLite is a lightweight database in a single file
- No server needed - just a file on your computer
- Super fast for local operations
- Works even without internet

This is the "quick notepad" - fast access, always available.
Data here gets synced to PostgreSQL later.
"""

import os
import sqlite3
from typing import Dict, Any, List, Optional
from datetime import datetime


# Database file location
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'theophysics.db')


def ensure_db_exists():
    """Make sure database file and tables exist."""
    # Ensure directory exists
    db_dir = os.path.dirname(DB_PATH)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)

    # Create tables if they don't exist
    conn = get_connection()
    cursor = conn.cursor()

    # Notes table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uuid TEXT UNIQUE NOT NULL,
            title TEXT,
            path TEXT NOT NULL,
            content_hash TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            synced INTEGER DEFAULT 0,
            synced_at TIMESTAMP
        )
    ''')

    # Tags table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uuid TEXT UNIQUE NOT NULL,
            type TEXT NOT NULL,
            content TEXT NOT NULL,
            note_uuid TEXT,
            parent_uuid TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            synced INTEGER DEFAULT 0,
            FOREIGN KEY (note_uuid) REFERENCES notes(uuid)
        )
    ''')

    # Definitions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS definitions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            term TEXT UNIQUE NOT NULL,
            short_definition TEXT,
            long_definition TEXT,
            source TEXT,
            source_url TEXT,
            cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            synced INTEGER DEFAULT 0
        )
    ''')

    # Links table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_uuid TEXT NOT NULL,
            to_uuid TEXT NOT NULL,
            link_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            synced INTEGER DEFAULT 0
        )
    ''')

    # Custom rules table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS custom_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trigger_word TEXT NOT NULL,
            prompt TEXT NOT NULL,
            enabled INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            synced INTEGER DEFAULT 0
        )
    ''')

    # Sync queue table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sync_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_name TEXT NOT NULL,
            record_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            queued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processed INTEGER DEFAULT 0
        )
    ''')

    # Semantic tree table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS semantic_tree (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uuid TEXT UNIQUE NOT NULL,
            level TEXT NOT NULL,
            parent_uuid TEXT,
            note_uuid TEXT,
            content TEXT,
            position INTEGER,
            FOREIGN KEY (note_uuid) REFERENCES notes(uuid)
        )
    ''')

    conn.commit()
    conn.close()


def get_connection() -> sqlite3.Connection:
    """Get a database connection."""
    ensure_directory()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    return conn


def ensure_directory():
    """Make sure the data directory exists."""
    db_dir = os.path.dirname(DB_PATH)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)


# ============================================
# GENERIC OPERATIONS
# ============================================

def save_to_sqlite(data: Dict[str, Any], table_name: str) -> int:
    """
    Save a record to a table.

    Args:
        data: Dictionary of column -> value
        table_name: Which table to save to

    Returns:
        The ID of the inserted row

    Example:
        save_to_sqlite({
            "term": "entropy",
            "short_definition": "Measure of disorder"
        }, "definitions")
    """
    ensure_db_exists()
    conn = get_connection()
    cursor = conn.cursor()

    columns = ', '.join(data.keys())
    placeholders = ', '.join(['?' for _ in data])
    values = tuple(data.values())

    cursor.execute(f'''
        INSERT OR REPLACE INTO {table_name} ({columns})
        VALUES ({placeholders})
    ''', values)

    row_id = cursor.lastrowid
    conn.commit()
    conn.close()

    # Add to sync queue
    queue_for_sync(table_name, row_id, 'insert')

    return row_id


def get_from_sqlite(query: str, params: List = None) -> List[Dict]:
    """
    Execute a query and return results.

    Args:
        query: SQL query
        params: Query parameters

    Returns:
        List of result rows as dictionaries

    Example:
        results = get_from_sqlite(
            "SELECT * FROM definitions WHERE term = ?",
            ["entropy"]
        )
    """
    ensure_db_exists()
    conn = get_connection()
    cursor = conn.cursor()

    if params:
        cursor.execute(query, params)
    else:
        cursor.execute(query)

    rows = cursor.fetchall()
    conn.close()

    # Convert to list of dictionaries
    return [dict(row) for row in rows]


def update_in_sqlite(table_name: str, record_id: int, data: Dict[str, Any]) -> bool:
    """
    Update a record.

    Args:
        table_name: Which table
        record_id: Row ID to update
        data: New values

    Returns:
        True if updated
    """
    ensure_db_exists()
    conn = get_connection()
    cursor = conn.cursor()

    set_clause = ', '.join([f'{k} = ?' for k in data.keys()])
    values = tuple(data.values()) + (record_id,)

    cursor.execute(f'''
        UPDATE {table_name}
        SET {set_clause}
        WHERE id = ?
    ''', values)

    conn.commit()
    success = cursor.rowcount > 0
    conn.close()

    if success:
        queue_for_sync(table_name, record_id, 'update')

    return success


def delete_from_sqlite(table_name: str, record_id: int) -> bool:
    """
    Delete a record.

    Args:
        table_name: Which table
        record_id: Row ID to delete

    Returns:
        True if deleted
    """
    ensure_db_exists()
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(f'DELETE FROM {table_name} WHERE id = ?', (record_id,))

    conn.commit()
    success = cursor.rowcount > 0
    conn.close()

    if success:
        queue_for_sync(table_name, record_id, 'delete')

    return success


# ============================================
# SYNC QUEUE
# ============================================

def queue_for_sync(table_name: str, record_id: int, action: str):
    """
    Add a record to the sync queue.

    Args:
        table_name: Which table was changed
        record_id: Which record
        action: 'insert', 'update', or 'delete'
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO sync_queue (table_name, record_id, action)
        VALUES (?, ?, ?)
    ''', (table_name, record_id, action))

    conn.commit()
    conn.close()


def get_pending_syncs() -> List[Dict]:
    """Get all items waiting to be synced to PostgreSQL."""
    return get_from_sqlite('''
        SELECT * FROM sync_queue
        WHERE processed = 0
        ORDER BY queued_at
    ''')


def mark_synced(sync_id: int):
    """Mark a sync queue item as processed."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE sync_queue
        SET processed = 1
        WHERE id = ?
    ''', (sync_id,))

    conn.commit()
    conn.close()


# ============================================
# SPECIALIZED QUERIES
# ============================================

def get_note_by_path(path: str) -> Optional[Dict]:
    """Find a note by its file path."""
    results = get_from_sqlite(
        "SELECT * FROM notes WHERE path = ? LIMIT 1",
        [path]
    )
    return results[0] if results else None


def get_note_by_uuid(uuid: str) -> Optional[Dict]:
    """Find a note by its UUID."""
    results = get_from_sqlite(
        "SELECT * FROM notes WHERE uuid = ? LIMIT 1",
        [uuid]
    )
    return results[0] if results else None


def get_tags_for_note(note_uuid: str) -> List[Dict]:
    """Get all tags for a specific note."""
    return get_from_sqlite(
        "SELECT * FROM tags WHERE note_uuid = ?",
        [note_uuid]
    )


def get_definition(term: str) -> Optional[Dict]:
    """Get a cached definition."""
    results = get_from_sqlite(
        "SELECT * FROM definitions WHERE term = ? LIMIT 1",
        [term.lower()]
    )
    return results[0] if results else None


def get_unsynced_count() -> Dict[str, int]:
    """Count unsynced records per table."""
    tables = ['notes', 'tags', 'definitions', 'links', 'custom_rules']
    counts = {}

    for table in tables:
        results = get_from_sqlite(
            f"SELECT COUNT(*) as count FROM {table} WHERE synced = 0"
        )
        counts[table] = results[0]['count'] if results else 0

    return counts


def mark_as_synced(table_name: str, record_id: int):
    """Mark a record as synced."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(f'''
        UPDATE {table_name}
        SET synced = 1, synced_at = ?
        WHERE id = ?
    ''', (datetime.now().isoformat(), record_id))

    conn.commit()
    conn.close()
