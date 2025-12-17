"""
Paper Scanner - Complete Auto-Scan and Link Pipeline

This module scans papers/notes for:
- Proper nouns (Einstein, Newton)
- Technical terms (entropy, axiom)
- Multi-word phrases (General Relativity)

Then automatically:
- Looks up definitions from Wikipedia
- Creates definition files in your vault
- Links terms in your notes
- Builds a database tracking every link

For beginners:
- This is the "brain" that reads your papers
- It finds important words and looks them up
- Creates a glossary automatically
- Tracks everything in a database
"""

import os
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

from linking.term_finder import find_terms, find_terms_in_content
from linking.definition_lookup import lookup_definition, create_definition_file, batch_lookup_definitions
from linking.auto_linker import auto_link_note, is_already_linked, add_link


def scan_paper(
    note_path: str,
    vault_path: str,
    auto_link: bool = True,
    fetch_definitions: bool = True,
    create_files: bool = True
) -> Dict[str, Any]:
    """
    Complete pipeline: Scan a paper, find terms, get definitions, create links.

    This is the MAIN function that does everything:
    1. Reads the paper
    2. Finds all proper nouns and terms
    3. Looks up each term (local → cache → Wikipedia)
    4. Creates definition files
    5. Links terms in the paper
    6. Records everything in the database

    Args:
        note_path: Path to the markdown file
        vault_path: Path to Obsidian vault
        auto_link: Whether to add links to the note
        fetch_definitions: Whether to fetch from Wikipedia
        create_files: Whether to create definition files

    Returns:
        Detailed summary of what was found and done

    Example:
        result = scan_paper("/vault/papers/physics.md", "/vault")
        # Returns:
        # {
        #     "note_path": "/vault/papers/physics.md",
        #     "terms_found": 15,
        #     "definitions_fetched": 12,
        #     "files_created": 10,
        #     "links_added": 8,
        #     "terms": [
        #         {"term": "Einstein", "type": "proper_noun", "linked": True, "has_definition": True},
        #         ...
        #     ]
        # }
    """
    from tags.uuid_manager import generate_uuid
    from database.sqlite_db import save_to_sqlite, get_from_sqlite

    result = {
        "note_path": note_path,
        "scanned_at": datetime.now().isoformat(),
        "terms_found": 0,
        "definitions_fetched": 0,
        "definitions_from_cache": 0,
        "files_created": 0,
        "links_added": 0,
        "terms": [],
        "errors": []
    }

    # Read the note
    try:
        with open(note_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        result["errors"].append(f"Failed to read file: {e}")
        return result

    # Step 1: Find all terms
    terms = find_terms(note_path)
    result["terms_found"] = len(terms)

    # Step 2: Process each term
    for term_data in terms:
        term = term_data['term']
        term_type = term_data.get('type', 'unknown')

        term_result = {
            "term": term,
            "type": term_type,
            "count": term_data.get('count', 1),
            "linked": False,
            "has_definition": False,
            "definition_source": None,
            "file_created": False
        }

        try:
            # Register term in the master registry
            register_term(term, term_type, note_path)

            # Record occurrence in this note
            record_term_occurrence(term, note_path, content)

            # Check if already linked
            if is_already_linked(content, term):
                term_result["linked"] = True

            # Look up definition
            if fetch_definitions:
                definition = lookup_definition(term, vault_path, create_files)

                if definition:
                    term_result["has_definition"] = True
                    term_result["definition_source"] = definition.get("source", "unknown")

                    if definition.get("cached"):
                        result["definitions_from_cache"] += 1
                    else:
                        result["definitions_fetched"] += 1

                    # Check if file was created
                    def_file = os.path.join(vault_path, "Definitions", f"{term.lower().replace(' ', '_')}.md")
                    if os.path.exists(def_file):
                        term_result["file_created"] = True
                        result["files_created"] += 1

        except Exception as e:
            result["errors"].append(f"Error processing term '{term}': {e}")

        result["terms"].append(term_result)

    # Step 3: Auto-link the note
    if auto_link:
        try:
            link_result = auto_link_note(note_path, vault_path)
            result["links_added"] = len(link_result.get("linked", []))

            # Update term results with link status
            for linked_term in link_result.get("linked", []):
                for term_result in result["terms"]:
                    if term_result["term"].lower() == linked_term.lower():
                        term_result["linked"] = True

        except Exception as e:
            result["errors"].append(f"Auto-linking failed: {e}")

    # Step 4: Record this scan in the database
    try:
        save_to_sqlite({
            "uuid": generate_uuid("scan"),
            "note_path": note_path,
            "terms_found": result["terms_found"],
            "terms_linked": result["links_added"],
            "terms_skipped": result["terms_found"] - result["links_added"],
            "processed_at": datetime.now().isoformat()
        }, "auto_link_history")
    except Exception:
        pass

    return result


def scan_folder(
    folder_path: str,
    vault_path: str,
    auto_link: bool = True,
    fetch_definitions: bool = True,
    create_files: bool = True,
    recursive: bool = True
) -> Dict[str, Any]:
    """
    Scan all papers in a folder.

    Args:
        folder_path: Folder containing papers
        vault_path: Vault path
        auto_link: Whether to add links
        fetch_definitions: Whether to fetch from Wikipedia
        create_files: Whether to create definition files
        recursive: Whether to scan subfolders

    Returns:
        Summary of all scans
    """
    result = {
        "folder_path": folder_path,
        "scanned_at": datetime.now().isoformat(),
        "notes_processed": 0,
        "total_terms_found": 0,
        "total_definitions_fetched": 0,
        "total_files_created": 0,
        "total_links_added": 0,
        "notes": [],
        "all_terms": {},  # term -> count across all notes
        "errors": []
    }

    # Find all .md files
    md_files = []

    if recursive:
        for root, dirs, files in os.walk(folder_path):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]

            for filename in files:
                if filename.endswith('.md'):
                    md_files.append(os.path.join(root, filename))
    else:
        for filename in os.listdir(folder_path):
            if filename.endswith('.md'):
                md_files.append(os.path.join(folder_path, filename))

    # Process each file
    for note_path in md_files:
        try:
            note_result = scan_paper(
                note_path, vault_path,
                auto_link, fetch_definitions, create_files
            )

            result["notes_processed"] += 1
            result["total_terms_found"] += note_result["terms_found"]
            result["total_definitions_fetched"] += note_result["definitions_fetched"]
            result["total_files_created"] += note_result["files_created"]
            result["total_links_added"] += note_result["links_added"]

            # Track terms across all notes
            for term_data in note_result["terms"]:
                term = term_data["term"]
                if term not in result["all_terms"]:
                    result["all_terms"][term] = {
                        "count": 0,
                        "notes": [],
                        "has_definition": term_data["has_definition"]
                    }
                result["all_terms"][term]["count"] += term_data["count"]
                result["all_terms"][term]["notes"].append(note_path)

            result["notes"].append({
                "path": note_path,
                "terms_found": note_result["terms_found"],
                "links_added": note_result["links_added"]
            })

        except Exception as e:
            result["errors"].append({
                "file": note_path,
                "error": str(e)
            })

    return result


def register_term(term: str, term_type: str, source_note: str = None) -> bool:
    """
    Register a term in the master term registry.

    This builds the database of every term ever seen.

    Args:
        term: The term
        term_type: proper_noun, keyword, phrase
        source_note: Where it was first found

    Returns:
        True if registered
    """
    from database.sqlite_db import get_from_sqlite, save_to_sqlite
    from tags.uuid_manager import generate_uuid

    try:
        # Check if term already exists
        existing = get_from_sqlite(
            "SELECT * FROM term_registry WHERE term = ? LIMIT 1",
            [term.lower()]
        )

        if existing:
            # Update occurrence count
            from database.sqlite_db import get_connection
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE term_registry
                SET occurrence_count = occurrence_count + 1,
                    last_seen = ?
                WHERE term = ?
            ''', (datetime.now().isoformat(), term.lower()))
            conn.commit()
            conn.close()
        else:
            # Create new entry
            save_to_sqlite({
                "uuid": generate_uuid("term"),
                "term": term.lower(),
                "term_type": term_type,
                "has_definition": 0,
                "occurrence_count": 1,
                "first_seen": datetime.now().isoformat(),
                "last_seen": datetime.now().isoformat()
            }, "term_registry")

        return True

    except Exception as e:
        print(f"Failed to register term: {e}")
        return False


def record_term_occurrence(term: str, note_path: str, content: str) -> bool:
    """
    Record where a term appears in a note.

    Args:
        term: The term
        note_path: Path to the note
        content: Note content

    Returns:
        True if recorded
    """
    from database.sqlite_db import save_to_sqlite
    from tags.uuid_manager import generate_uuid

    try:
        # Find the term in content
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if term.lower() in line.lower():
                # Record this occurrence
                save_to_sqlite({
                    "uuid": generate_uuid("occur"),
                    "term": term.lower(),
                    "note_path": note_path,
                    "line_number": i + 1,
                    "context": line[:200],  # First 200 chars of line
                    "linked": 0,
                    "created_at": datetime.now().isoformat()
                }, "term_occurrences")
                break  # Only record first occurrence per note

        return True

    except Exception:
        return False


def get_term_statistics() -> Dict[str, Any]:
    """
    Get statistics about all terms in the database.

    Returns:
        Summary of term data
    """
    from database.sqlite_db import get_from_sqlite

    try:
        # Total terms
        total = get_from_sqlite("SELECT COUNT(*) as count FROM term_registry")
        total_count = total[0]['count'] if total else 0

        # Terms with definitions
        with_defs = get_from_sqlite(
            "SELECT COUNT(*) as count FROM term_registry WHERE has_definition = 1"
        )
        with_defs_count = with_defs[0]['count'] if with_defs else 0

        # Top terms by occurrence
        top_terms = get_from_sqlite('''
            SELECT term, occurrence_count, term_type
            FROM term_registry
            ORDER BY occurrence_count DESC
            LIMIT 20
        ''')

        # Terms by type
        by_type = get_from_sqlite('''
            SELECT term_type, COUNT(*) as count
            FROM term_registry
            GROUP BY term_type
        ''')

        # Recent terms
        recent = get_from_sqlite('''
            SELECT term, first_seen
            FROM term_registry
            ORDER BY first_seen DESC
            LIMIT 10
        ''')

        return {
            "total_terms": total_count,
            "with_definitions": with_defs_count,
            "without_definitions": total_count - with_defs_count,
            "top_terms": [dict(t) for t in top_terms],
            "by_type": [dict(t) for t in by_type],
            "recent_terms": [dict(t) for t in recent]
        }

    except Exception as e:
        return {"error": str(e)}


def get_term_occurrences(term: str) -> List[Dict]:
    """
    Get all places where a term appears.

    Args:
        term: The term to find

    Returns:
        List of occurrences with note paths and contexts
    """
    from database.sqlite_db import get_from_sqlite

    try:
        occurrences = get_from_sqlite('''
            SELECT note_path, line_number, context, linked, created_at
            FROM term_occurrences
            WHERE term = ?
            ORDER BY created_at DESC
        ''', [term.lower()])

        return [dict(o) for o in occurrences]

    except Exception:
        return []


def find_unlinked_terms() -> List[Dict]:
    """
    Find all terms that exist but haven't been linked.

    Returns:
        List of terms needing attention
    """
    from database.sqlite_db import get_from_sqlite

    try:
        unlinked = get_from_sqlite('''
            SELECT t.term, t.occurrence_count, t.term_type,
                   (SELECT COUNT(*) FROM term_occurrences o
                    WHERE o.term = t.term AND o.linked = 0) as unlinked_count
            FROM term_registry t
            WHERE t.has_definition = 0
            ORDER BY t.occurrence_count DESC
            LIMIT 50
        ''')

        return [dict(t) for t in unlinked]

    except Exception:
        return []


def mark_term_as_linked(term: str, note_path: str) -> bool:
    """
    Mark a term as linked in a specific note.

    Args:
        term: The term
        note_path: The note where it was linked

    Returns:
        True if updated
    """
    from database.sqlite_db import get_connection

    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE term_occurrences
            SET linked = 1
            WHERE term = ? AND note_path = ?
        ''', (term.lower(), note_path))
        conn.commit()
        conn.close()
        return True

    except Exception:
        return False


def update_term_definition_status(term: str, has_definition: bool, source: str = None) -> bool:
    """
    Update whether a term has a definition.

    Args:
        term: The term
        has_definition: Whether it has a definition
        source: Where the definition came from

    Returns:
        True if updated
    """
    from database.sqlite_db import get_connection

    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE term_registry
            SET has_definition = ?, definition_source = ?
            WHERE term = ?
        ''', (1 if has_definition else 0, source, term.lower()))
        conn.commit()
        conn.close()
        return True

    except Exception:
        return False


def add_manual_term(term: str, definition: str, vault_path: str) -> Dict[str, Any]:
    """
    Manually add a term that the system missed.

    Args:
        term: The term
        definition: Your custom definition
        vault_path: Where to create the file

    Returns:
        Result of the operation
    """
    from linking.definition_lookup import create_definition_file

    result = {
        "term": term,
        "success": False,
        "file_path": None
    }

    try:
        # Register the term
        register_term(term, "manual", None)

        # Create definition file
        definition_data = {
            "short_definition": definition,
            "source": "manual",
            "source_url": None
        }

        file_path = create_definition_file(term, definition_data, vault_path)
        result["file_path"] = file_path
        result["success"] = True

        # Update term status
        update_term_definition_status(term, True, "manual")

    except Exception as e:
        result["error"] = str(e)

    return result
