"""
Vault Scanner

Scans the Obsidian vault for changes.

For beginners:
- This watches your vault for new or modified files
- Compares file timestamps to database records
- Returns a list of files that need processing
- Helps keep everything in sync
"""

import os
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional

from database.sqlite_db import get_note_by_path, save_to_sqlite, get_from_sqlite


def scan_vault(vault_path: str) -> Dict[str, Any]:
    """
    Scan a vault and find all changes.

    Args:
        vault_path: Path to Obsidian vault

    Returns:
        Summary of changes found

    Example:
        changes = scan_vault("/path/to/vault")
        # Returns:
        # {
        #     "new": ["new_file.md", "another_new.md"],
        #     "modified": ["changed_file.md"],
        #     "deleted": ["removed_file.md"],
        #     "unchanged": 45,
        #     "total_scanned": 48
        # }
    """
    result = {
        "new": [],
        "modified": [],
        "deleted": [],
        "unchanged": 0,
        "total_scanned": 0,
        "errors": []
    }

    # Get all known notes from database
    known_notes = get_all_known_notes()
    known_paths = {n['path']: n for n in known_notes}

    # Scan vault for .md files
    found_paths = set()

    for root, dirs, files in os.walk(vault_path):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.')]

        for filename in files:
            if filename.endswith('.md'):
                file_path = os.path.join(root, filename)
                found_paths.add(file_path)
                result["total_scanned"] += 1

                try:
                    status = check_file_status(file_path, known_paths)

                    if status == 'new':
                        result["new"].append(file_path)
                    elif status == 'modified':
                        result["modified"].append(file_path)
                    else:
                        result["unchanged"] += 1

                except Exception as e:
                    result["errors"].append({
                        "file": file_path,
                        "error": str(e)
                    })

    # Find deleted files
    for path in known_paths:
        if path not in found_paths:
            result["deleted"].append(path)

    return result


def get_all_known_notes() -> List[Dict]:
    """Get all notes from the database."""
    return get_from_sqlite("SELECT * FROM notes")


def check_file_status(file_path: str, known_paths: Dict) -> str:
    """
    Check if a file is new, modified, or unchanged.

    Args:
        file_path: Path to check
        known_paths: Dictionary of known notes

    Returns:
        'new', 'modified', or 'unchanged'
    """
    # Calculate current file hash
    current_hash = get_file_hash(file_path)

    if file_path not in known_paths:
        return 'new'

    # Compare hashes
    known_note = known_paths[file_path]
    stored_hash = known_note.get('content_hash')

    if stored_hash != current_hash:
        return 'modified'

    return 'unchanged'


def get_file_hash(file_path: str) -> str:
    """
    Calculate MD5 hash of file content.

    Args:
        file_path: Path to file

    Returns:
        Hash string
    """
    hasher = hashlib.md5()

    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hasher.update(chunk)

    return hasher.hexdigest()


def get_file_modified_time(file_path: str) -> datetime:
    """
    Get file modification time.

    Args:
        file_path: Path to file

    Returns:
        Datetime of last modification
    """
    timestamp = os.path.getmtime(file_path)
    return datetime.fromtimestamp(timestamp)


def register_note(file_path: str, vault_path: str = None) -> Dict[str, Any]:
    """
    Register a new note in the database.

    Args:
        file_path: Path to note
        vault_path: Base vault path (for relative path)

    Returns:
        Created note record
    """
    from tags.uuid_manager import generate_uuid

    # Get file info
    content_hash = get_file_hash(file_path)
    modified_at = get_file_modified_time(file_path)

    # Extract title
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    from semantic.tree_builder import extract_title
    title = extract_title(content, file_path)

    # Create record
    note = {
        "uuid": generate_uuid('note'),
        "title": title,
        "path": file_path,
        "content_hash": content_hash,
        "modified_at": modified_at.isoformat(),
        "synced": 0
    }

    save_to_sqlite(note, 'notes')

    return note


def update_note_hash(file_path: str) -> bool:
    """
    Update the stored hash for a note.

    Args:
        file_path: Path to note

    Returns:
        True if updated
    """
    from database.sqlite_db import update_in_sqlite, get_note_by_path

    note = get_note_by_path(file_path)
    if not note:
        return False

    new_hash = get_file_hash(file_path)
    modified_at = get_file_modified_time(file_path)

    update_in_sqlite('notes', note['id'], {
        'content_hash': new_hash,
        'modified_at': modified_at.isoformat(),
        'synced': 0
    })

    return True


def get_notes_needing_processing(vault_path: str) -> List[str]:
    """
    Get list of notes that need classification.

    Args:
        vault_path: Path to vault

    Returns:
        List of file paths
    """
    changes = scan_vault(vault_path)
    return changes['new'] + changes['modified']


def watch_vault(vault_path: str, callback, interval: int = 5):
    """
    Watch vault for changes (simple polling version).

    Args:
        vault_path: Path to watch
        callback: Function to call when changes found
        interval: Seconds between checks

    Note: For production, use watchdog library instead.
    """
    import time

    print(f"Watching vault: {vault_path}")
    print(f"Checking every {interval} seconds...")
    print("Press Ctrl+C to stop")

    try:
        while True:
            changes = scan_vault(vault_path)

            if changes['new'] or changes['modified'] or changes['deleted']:
                callback(changes)

            time.sleep(interval)

    except KeyboardInterrupt:
        print("\nStopped watching.")
