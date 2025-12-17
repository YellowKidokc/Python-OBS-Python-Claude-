"""
PostgreSQL Database Layer

Global database for permanent storage and multi-device sync.

For beginners:
- PostgreSQL is a powerful database server
- Runs separately (on your machine or in the cloud)
- Can handle huge amounts of data
- Supports multiple users/devices
- Great for analytics and dashboards

This is the "permanent filing cabinet" - the official record.
SQLite syncs here regularly.
"""

import os
from typing import Dict, Any, List, Optional
from datetime import datetime

# You'll need: pip install psycopg2-binary
# For now, we'll handle ImportError gracefully
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False


# Connection settings (from environment or config)
PG_CONFIG = {
    'host': os.environ.get('PG_HOST', 'localhost'),
    'port': os.environ.get('PG_PORT', '5432'),
    'database': os.environ.get('PG_DATABASE', 'theophysics'),
    'user': os.environ.get('PG_USER', 'postgres'),
    'password': os.environ.get('PG_PASSWORD', '')
}


def check_connection() -> bool:
    """
    Check if we can connect to PostgreSQL.

    Returns:
        True if connection successful
    """
    if not HAS_PSYCOPG2:
        return False

    try:
        conn = get_connection()
        conn.close()
        return True
    except Exception:
        return False


def get_connection():
    """
    Get a PostgreSQL connection.

    Returns:
        Database connection

    Raises:
        Exception if connection fails
    """
    if not HAS_PSYCOPG2:
        raise ImportError(
            "psycopg2 not installed. Run: pip install psycopg2-binary"
        )

    return psycopg2.connect(
        host=PG_CONFIG['host'],
        port=PG_CONFIG['port'],
        database=PG_CONFIG['database'],
        user=PG_CONFIG['user'],
        password=PG_CONFIG['password']
    )


def init_database():
    """
    Create all tables in PostgreSQL.

    Run this once to set up the database.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Notes table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            id SERIAL PRIMARY KEY,
            uuid VARCHAR(50) UNIQUE NOT NULL,
            title TEXT,
            path TEXT NOT NULL,
            content_hash TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            synced_from VARCHAR(50)
        )
    ''')

    # Tags table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tags (
            id SERIAL PRIMARY KEY,
            uuid VARCHAR(50) UNIQUE NOT NULL,
            type VARCHAR(50) NOT NULL,
            content TEXT NOT NULL,
            note_uuid VARCHAR(50) REFERENCES notes(uuid),
            parent_uuid VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            synced_from VARCHAR(50)
        )
    ''')

    # Definitions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS definitions (
            id SERIAL PRIMARY KEY,
            term TEXT UNIQUE NOT NULL,
            short_definition TEXT,
            long_definition TEXT,
            source TEXT,
            source_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            synced_from VARCHAR(50)
        )
    ''')

    # Links table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS links (
            id SERIAL PRIMARY KEY,
            from_uuid VARCHAR(50) NOT NULL,
            to_uuid VARCHAR(50) NOT NULL,
            link_type VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Semantic graph table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS semantic_graph (
            id SERIAL PRIMARY KEY,
            uuid VARCHAR(50) UNIQUE NOT NULL,
            level VARCHAR(20) NOT NULL,
            parent_uuid VARCHAR(50),
            note_uuid VARCHAR(50) REFERENCES notes(uuid),
            content TEXT,
            position INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Embeddings table (for AI/RAG)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS embeddings (
            id SERIAL PRIMARY KEY,
            uuid VARCHAR(50) NOT NULL,
            entity_type VARCHAR(50) NOT NULL,
            embedding BYTEA,
            model_name VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Custom rules table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS custom_rules (
            id SERIAL PRIMARY KEY,
            trigger_word TEXT NOT NULL,
            prompt TEXT NOT NULL,
            enabled BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Sync logs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sync_logs (
            id SERIAL PRIMARY KEY,
            source_id VARCHAR(50),
            table_name VARCHAR(50) NOT NULL,
            records_synced INTEGER DEFAULT 0,
            synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status VARCHAR(20),
            error_message TEXT
        )
    ''')

    # Create indexes for common queries
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_tags_note ON tags(note_uuid);
        CREATE INDEX IF NOT EXISTS idx_tags_type ON tags(type);
        CREATE INDEX IF NOT EXISTS idx_links_from ON links(from_uuid);
        CREATE INDEX IF NOT EXISTS idx_links_to ON links(to_uuid);
        CREATE INDEX IF NOT EXISTS idx_semantic_note ON semantic_graph(note_uuid);
        CREATE INDEX IF NOT EXISTS idx_embeddings_uuid ON embeddings(uuid);
    ''')

    conn.commit()
    conn.close()


# ============================================
# SYNC OPERATIONS
# ============================================

def sync_to_postgres() -> Dict[str, Any]:
    """
    Sync all pending changes from SQLite to PostgreSQL.

    Returns:
        Summary of sync operation
    """
    from database.sqlite_db import get_pending_syncs, mark_synced, get_from_sqlite

    result = {
        "synced": 0,
        "failed": 0,
        "errors": []
    }

    # Check connection first
    if not check_connection():
        result["errors"].append("Cannot connect to PostgreSQL")
        return result

    conn = get_connection()
    cursor = conn.cursor()

    # Get pending syncs
    pending = get_pending_syncs()

    for item in pending:
        try:
            table = item['table_name']
            record_id = item['record_id']
            action = item['action']

            # Get the actual record from SQLite
            records = get_from_sqlite(
                f"SELECT * FROM {table} WHERE id = ?",
                [record_id]
            )

            if not records and action != 'delete':
                continue

            if action == 'delete':
                # Delete from Postgres
                cursor.execute(
                    f"DELETE FROM {table} WHERE id = %s",
                    (record_id,)
                )

            elif action in ('insert', 'update'):
                record = records[0]
                # Remove SQLite-specific fields
                record.pop('synced', None)
                record.pop('synced_at', None)

                # Upsert (insert or update)
                columns = list(record.keys())
                values = list(record.values())

                # Build upsert query
                cols_str = ', '.join(columns)
                vals_str = ', '.join(['%s'] * len(values))
                update_str = ', '.join([f'{c} = EXCLUDED.{c}' for c in columns if c != 'id'])

                query = f'''
                    INSERT INTO {table} ({cols_str})
                    VALUES ({vals_str})
                    ON CONFLICT (id) DO UPDATE SET {update_str}
                '''

                cursor.execute(query, values)

            # Mark as synced in SQLite
            mark_synced(item['id'])
            result["synced"] += 1

        except Exception as e:
            result["failed"] += 1
            result["errors"].append(str(e))

    # Log the sync
    cursor.execute('''
        INSERT INTO sync_logs (table_name, records_synced, status)
        VALUES (%s, %s, %s)
    ''', ('all', result["synced"], 'success' if not result["errors"] else 'partial'))

    conn.commit()
    conn.close()

    return result


def pull_from_postgres(uuid: str, table: str = 'notes') -> Optional[Dict]:
    """
    Get a specific record from PostgreSQL.

    Args:
        uuid: UUID to find
        table: Which table

    Returns:
        Record if found
    """
    if not check_connection():
        return None

    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute(
        f"SELECT * FROM {table} WHERE uuid = %s LIMIT 1",
        (uuid,)
    )

    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def full_sync_from_postgres(table: str = None) -> Dict[str, int]:
    """
    Pull all data from PostgreSQL to SQLite.

    Useful for syncing a new device.

    Args:
        table: Specific table to sync (None for all)

    Returns:
        Count of records synced per table
    """
    from database.sqlite_db import save_to_sqlite

    tables = [table] if table else [
        'notes', 'tags', 'definitions', 'links', 'custom_rules'
    ]

    result = {}

    if not check_connection():
        return result

    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    for t in tables:
        cursor.execute(f"SELECT * FROM {t}")
        rows = cursor.fetchall()

        for row in rows:
            row_dict = dict(row)
            row_dict['synced'] = 1  # Already synced
            save_to_sqlite(row_dict, t)

        result[t] = len(rows)

    conn.close()
    return result


# ============================================
# ANALYTICS QUERIES
# ============================================

def get_tag_statistics() -> Dict[str, Any]:
    """
    Get statistics about all tags.

    Returns:
        Counts and breakdowns
    """
    if not check_connection():
        return {}

    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    # Count by type
    cursor.execute('''
        SELECT type, COUNT(*) as count
        FROM tags
        GROUP BY type
        ORDER BY count DESC
    ''')
    by_type = cursor.fetchall()

    # Total count
    cursor.execute('SELECT COUNT(*) as total FROM tags')
    total = cursor.fetchone()['total']

    # Recent activity
    cursor.execute('''
        SELECT DATE(created_at) as date, COUNT(*) as count
        FROM tags
        WHERE created_at > CURRENT_DATE - INTERVAL '7 days'
        GROUP BY DATE(created_at)
        ORDER BY date DESC
    ''')
    recent = cursor.fetchall()

    conn.close()

    return {
        "total": total,
        "by_type": [dict(r) for r in by_type],
        "recent_activity": [dict(r) for r in recent]
    }


def get_notes_without_tags() -> List[Dict]:
    """Find notes that haven't been classified."""
    if not check_connection():
        return []

    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute('''
        SELECT n.*
        FROM notes n
        LEFT JOIN tags t ON n.uuid = t.note_uuid
        WHERE t.id IS NULL
    ''')

    rows = cursor.fetchall()
    conn.close()

    return [dict(r) for r in rows]


def search_tags(query: str) -> List[Dict]:
    """
    Search for tags by content.

    Args:
        query: Search term

    Returns:
        Matching tags
    """
    if not check_connection():
        return []

    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute('''
        SELECT t.*, n.title as note_title, n.path as note_path
        FROM tags t
        LEFT JOIN notes n ON t.note_uuid = n.uuid
        WHERE t.content ILIKE %s
        ORDER BY t.created_at DESC
        LIMIT 50
    ''', (f'%{query}%',))

    rows = cursor.fetchall()
    conn.close()

    return [dict(r) for r in rows]
