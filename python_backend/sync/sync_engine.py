"""
Sync Engine

Orchestrates synchronization between:
- Vault files
- SQLite (local cache)
- PostgreSQL (global storage)

For beginners:
- This is the "traffic controller" for data
- Makes sure everything stays up to date
- Handles conflicts and errors gracefully
"""

from datetime import datetime
from typing import Dict, Any, List

from database.sqlite_db import (
    get_pending_syncs, mark_synced, get_from_sqlite,
    get_unsynced_count, save_to_sqlite
)
from database.postgres_db import sync_to_postgres, check_connection
from sync.vault_scanner import (
    scan_vault, register_note, update_note_hash
)


def perform_sync(vault_path: str = None) -> Dict[str, Any]:
    """
    Perform a full sync operation.

    Steps:
    1. Scan vault for file changes
    2. Update SQLite with changes
    3. Sync SQLite to PostgreSQL

    Args:
        vault_path: Optional vault path to scan

    Returns:
        Summary of sync operation
    """
    result = {
        "timestamp": datetime.now().isoformat(),
        "vault_scan": None,
        "sqlite_updates": 0,
        "postgres_sync": None,
        "status": "success",
        "errors": []
    }

    # Step 1: Scan vault (if path provided)
    if vault_path:
        try:
            vault_changes = scan_vault(vault_path)
            result["vault_scan"] = vault_changes

            # Register new files
            for file_path in vault_changes['new']:
                try:
                    register_note(file_path, vault_path)
                    result["sqlite_updates"] += 1
                except Exception as e:
                    result["errors"].append(f"Failed to register {file_path}: {e}")

            # Update modified files
            for file_path in vault_changes['modified']:
                try:
                    update_note_hash(file_path)
                    result["sqlite_updates"] += 1
                except Exception as e:
                    result["errors"].append(f"Failed to update {file_path}: {e}")

        except Exception as e:
            result["errors"].append(f"Vault scan failed: {e}")

    # Step 2: Sync to PostgreSQL
    if check_connection():
        try:
            pg_result = sync_to_postgres()
            result["postgres_sync"] = pg_result
        except Exception as e:
            result["errors"].append(f"PostgreSQL sync failed: {e}")
    else:
        result["postgres_sync"] = {"status": "skipped", "reason": "No connection"}

    # Set overall status
    if result["errors"]:
        result["status"] = "partial" if result["sqlite_updates"] > 0 else "failed"

    return result


def get_sync_status() -> Dict[str, Any]:
    """
    Get current sync status.

    Returns:
        Status information
    """
    unsynced = get_unsynced_count()
    pending = len(get_pending_syncs())
    pg_available = check_connection()

    return {
        "sqlite_pending": unsynced,
        "sync_queue_size": pending,
        "postgres_available": pg_available,
        "last_check": datetime.now().isoformat()
    }


def force_resync_note(note_path: str) -> Dict[str, Any]:
    """
    Force a complete resync of a single note.

    Args:
        note_path: Path to note

    Returns:
        Result of resync
    """
    from tags.tag_parser import parse_tags
    from semantic.tree_builder import build_semantic_tree

    result = {
        "note_path": note_path,
        "actions": [],
        "errors": []
    }

    try:
        # Update note hash
        update_note_hash(note_path)
        result["actions"].append("Updated note hash")

        # Re-parse tags
        tags = parse_tags(note_path)
        result["actions"].append(f"Parsed {len(tags)} tags")

        # Rebuild semantic tree
        tree = build_semantic_tree(note_path)
        result["actions"].append("Rebuilt semantic tree")

        # Sync to PostgreSQL if available
        if check_connection():
            sync_to_postgres()
            result["actions"].append("Synced to PostgreSQL")

    except Exception as e:
        result["errors"].append(str(e))

    return result


def incremental_sync() -> Dict[str, Any]:
    """
    Perform incremental sync (only changed items).

    More efficient than full sync.
    """
    result = {
        "synced_items": 0,
        "tables": {}
    }

    pending = get_pending_syncs()

    if not pending:
        return result

    if not check_connection():
        result["status"] = "skipped"
        result["reason"] = "PostgreSQL not available"
        return result

    pg_result = sync_to_postgres()
    result["synced_items"] = pg_result.get("synced", 0)
    result["errors"] = pg_result.get("errors", [])

    return result


def resolve_conflict(local_data: Dict, remote_data: Dict, strategy: str = 'local_wins') -> Dict:
    """
    Resolve a sync conflict between local and remote data.

    Args:
        local_data: Data from SQLite
        remote_data: Data from PostgreSQL
        strategy: 'local_wins', 'remote_wins', or 'newest_wins'

    Returns:
        Resolved data
    """
    if strategy == 'local_wins':
        return local_data

    elif strategy == 'remote_wins':
        return remote_data

    elif strategy == 'newest_wins':
        local_time = local_data.get('modified_at') or local_data.get('created_at')
        remote_time = remote_data.get('modified_at') or remote_data.get('created_at')

        if local_time and remote_time:
            if local_time > remote_time:
                return local_data
            else:
                return remote_data

        # Default to local if can't compare
        return local_data

    else:
        raise ValueError(f"Unknown strategy: {strategy}")


def schedule_sync(interval_minutes: int = 5):
    """
    Schedule periodic syncs.

    Args:
        interval_minutes: Minutes between syncs

    Note: For production, use a proper scheduler like APScheduler.
    """
    import time
    import threading

    def sync_loop():
        while True:
            try:
                result = incremental_sync()
                print(f"[Sync] Synced {result.get('synced_items', 0)} items")
            except Exception as e:
                print(f"[Sync] Error: {e}")

            time.sleep(interval_minutes * 60)

    thread = threading.Thread(target=sync_loop, daemon=True)
    thread.start()
    print(f"[Sync] Scheduled every {interval_minutes} minutes")


def export_sqlite_to_json(output_path: str) -> bool:
    """
    Export SQLite database to JSON (for backup).

    Args:
        output_path: Where to save JSON

    Returns:
        True if successful
    """
    import json

    tables = ['notes', 'tags', 'definitions', 'links', 'custom_rules']
    export_data = {}

    for table in tables:
        try:
            rows = get_from_sqlite(f"SELECT * FROM {table}")
            export_data[table] = rows
        except Exception as e:
            export_data[table] = {"error": str(e)}

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, default=str)

    return True


def import_from_json(input_path: str) -> Dict[str, int]:
    """
    Import data from JSON backup.

    Args:
        input_path: Path to JSON file

    Returns:
        Count of imported records per table
    """
    import json

    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    results = {}

    for table, rows in data.items():
        if isinstance(rows, list):
            count = 0
            for row in rows:
                try:
                    save_to_sqlite(row, table)
                    count += 1
                except Exception:
                    pass
            results[table] = count

    return results
