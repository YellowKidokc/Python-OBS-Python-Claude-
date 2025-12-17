"""
Link Preview & Confirmation System

Shows user what will be linked BEFORE it happens.
Allows turning off links per paper, per word, or globally.

For beginners:
- Before auto-linking, this shows a preview
- User can approve, reject, or modify
- Settings persist (if you turn off "the", it stays off)
- Tracks all actions for undo capability
"""

import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from database.sqlite_db import save_to_sqlite, get_from_sqlite, get_connection
from tags.uuid_manager import generate_uuid


# ============================================
# LINK SETTINGS (What to link, what to skip)
# ============================================

def get_link_settings() -> Dict[str, Any]:
    """
    Get all link settings (disabled words, papers, etc.)

    Returns:
        Settings dictionary
    """
    try:
        # Get disabled terms (globally)
        disabled_terms = get_from_sqlite(
            "SELECT term FROM link_settings WHERE setting_type = 'disabled_term'"
        )

        # Get disabled papers (don't auto-link these)
        disabled_papers = get_from_sqlite(
            "SELECT value FROM link_settings WHERE setting_type = 'disabled_paper'"
        )

        # Get paper-specific disabled terms
        paper_disabled = get_from_sqlite(
            "SELECT term, value as paper_path FROM link_settings WHERE setting_type = 'disabled_term_in_paper'"
        )

        # Get user preferences
        prefs = get_from_sqlite(
            "SELECT setting_type, value FROM link_settings WHERE setting_type LIKE 'pref_%'"
        )

        return {
            "disabled_terms": [r['term'] for r in disabled_terms],
            "disabled_papers": [r['value'] for r in disabled_papers],
            "paper_disabled_terms": [{"term": r['term'], "paper": r['paper_path']} for r in paper_disabled],
            "preferences": {r['setting_type']: r['value'] for r in prefs},
            "show_preview": get_preference("show_preview", "true") == "true",
            "link_all_occurrences": get_preference("link_all_occurrences", "true") == "true"
        }
    except Exception:
        return {
            "disabled_terms": [],
            "disabled_papers": [],
            "paper_disabled_terms": [],
            "preferences": {},
            "show_preview": True,
            "link_all_occurrences": True
        }


def disable_term_globally(term: str) -> bool:
    """
    Turn off linking for a term everywhere.

    Args:
        term: Word to never link

    Returns:
        True if saved
    """
    try:
        save_to_sqlite({
            "uuid": generate_uuid("setting"),
            "setting_type": "disabled_term",
            "term": term.lower(),
            "value": "disabled",
            "created_at": datetime.now().isoformat()
        }, "link_settings")
        return True
    except Exception:
        return False


def disable_term_in_paper(term: str, paper_path: str) -> bool:
    """
    Turn off linking for a term in a specific paper only.

    Args:
        term: Word to not link
        paper_path: Which paper

    Returns:
        True if saved
    """
    try:
        save_to_sqlite({
            "uuid": generate_uuid("setting"),
            "setting_type": "disabled_term_in_paper",
            "term": term.lower(),
            "value": paper_path,
            "created_at": datetime.now().isoformat()
        }, "link_settings")
        return True
    except Exception:
        return False


def disable_paper(paper_path: str) -> bool:
    """
    Turn off ALL auto-linking for a specific paper.

    Args:
        paper_path: Paper to exclude

    Returns:
        True if saved
    """
    try:
        save_to_sqlite({
            "uuid": generate_uuid("setting"),
            "setting_type": "disabled_paper",
            "term": "",
            "value": paper_path,
            "created_at": datetime.now().isoformat()
        }, "link_settings")
        return True
    except Exception:
        return False


def enable_term(term: str, paper_path: str = None) -> bool:
    """
    Re-enable linking for a term.

    Args:
        term: Word to re-enable
        paper_path: If provided, only re-enable for this paper

    Returns:
        True if updated
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()

        if paper_path:
            cursor.execute('''
                DELETE FROM link_settings
                WHERE term = ? AND value = ? AND setting_type = 'disabled_term_in_paper'
            ''', (term.lower(), paper_path))
        else:
            cursor.execute('''
                DELETE FROM link_settings
                WHERE term = ? AND setting_type = 'disabled_term'
            ''', (term.lower(),))

        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def set_preference(pref_name: str, value: str) -> bool:
    """
    Set a user preference.

    Args:
        pref_name: Preference name (show_preview, link_all_occurrences, etc.)
        value: Value to set

    Returns:
        True if saved
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Delete existing
        cursor.execute('''
            DELETE FROM link_settings WHERE setting_type = ?
        ''', (f"pref_{pref_name}",))

        # Insert new
        cursor.execute('''
            INSERT INTO link_settings (uuid, setting_type, term, value, created_at)
            VALUES (?, ?, '', ?, ?)
        ''', (generate_uuid("pref"), f"pref_{pref_name}", value, datetime.now().isoformat()))

        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def get_preference(pref_name: str, default: str = "") -> str:
    """
    Get a user preference.

    Args:
        pref_name: Preference name
        default: Default value if not set

    Returns:
        Preference value
    """
    try:
        result = get_from_sqlite(
            "SELECT value FROM link_settings WHERE setting_type = ? LIMIT 1",
            [f"pref_{pref_name}"]
        )
        return result[0]['value'] if result else default
    except Exception:
        return default


# ============================================
# LINK PREVIEW (Show before linking)
# ============================================

def generate_link_preview(
    note_path: str,
    vault_path: str,
    terms: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Generate a preview of what will be linked.

    This is what the popup shows BEFORE linking happens.

    Args:
        note_path: Paper being processed
        vault_path: Vault path
        terms: List of terms found

    Returns:
        Preview data for UI to display

    Example return:
        {
            "note_path": "/vault/paper.md",
            "total_terms": 15,
            "will_link": [
                {
                    "term": "Einstein",
                    "occurrences": 5,
                    "has_definition": True,
                    "sources": ["glossary", "wikipedia"],
                    "action": "link"
                }
            ],
            "will_skip": [
                {
                    "term": "the",
                    "reason": "disabled_globally"
                }
            ],
            "needs_definition": ["some_term"],
            "estimated_api_calls": 3
        }
    """
    settings = get_link_settings()

    preview = {
        "note_path": note_path,
        "total_terms": len(terms),
        "will_link": [],
        "will_skip": [],
        "needs_definition": [],
        "estimated_api_calls": 0,
        "can_proceed": True
    }

    # Check if paper is disabled
    if note_path in settings["disabled_papers"]:
        preview["can_proceed"] = False
        preview["skip_reason"] = "Paper has auto-linking disabled"
        return preview

    for term_data in terms:
        term = term_data['term']
        term_lower = term.lower()

        # Check if term is disabled globally
        if term_lower in settings["disabled_terms"]:
            preview["will_skip"].append({
                "term": term,
                "reason": "disabled_globally",
                "can_enable": True
            })
            continue

        # Check if term is disabled for this paper
        paper_disabled = [p for p in settings["paper_disabled_terms"]
                         if p['term'] == term_lower and p['paper'] == note_path]
        if paper_disabled:
            preview["will_skip"].append({
                "term": term,
                "reason": "disabled_for_this_paper",
                "can_enable": True
            })
            continue

        # Check if we have a definition
        sources = get_available_sources(term, vault_path)

        if sources:
            preview["will_link"].append({
                "term": term,
                "occurrences": term_data.get('count', 1),
                "has_definition": True,
                "sources": sources,
                "action": "link"
            })
        else:
            # Need to fetch definition
            preview["will_link"].append({
                "term": term,
                "occurrences": term_data.get('count', 1),
                "has_definition": False,
                "sources": [],
                "action": "fetch_and_link"
            })
            preview["needs_definition"].append(term)
            preview["estimated_api_calls"] += 1

    return preview


def get_available_sources(term: str, vault_path: str) -> List[Dict[str, str]]:
    """
    Get all available sources for a term's definition.

    Args:
        term: The term
        vault_path: Vault path

    Returns:
        List of sources with URLs
    """
    sources = []

    # Check local glossary
    def_file = os.path.join(vault_path, "Definitions", f"{term.lower().replace(' ', '_')}.md")
    if os.path.exists(def_file):
        sources.append({
            "name": "Glossary",
            "type": "local",
            "path": def_file
        })

    # Check if we have cached external sources
    try:
        cached = get_from_sqlite(
            "SELECT source, source_url FROM definitions WHERE term = ?",
            [term.lower()]
        )
        for c in cached:
            if c['source'] == 'wikipedia':
                sources.append({
                    "name": "Wikipedia",
                    "type": "external",
                    "url": c['source_url']
                })
            elif c['source'] == 'stanford':
                sources.append({
                    "name": "Stanford Encyclopedia",
                    "type": "external",
                    "url": c['source_url']
                })
    except Exception:
        pass

    return sources


# ============================================
# ACTION LOG (Running list of what's happening)
# ============================================

def log_action(
    action_type: str,
    term: str = None,
    note_path: str = None,
    details: Dict = None,
    reversible: bool = True
) -> str:
    """
    Log an action to the running action list.

    Args:
        action_type: What happened (link_added, definition_fetched, etc.)
        term: Term involved
        note_path: Paper involved
        details: Additional details
        reversible: Can this be undone?

    Returns:
        Action UUID (for undo)
    """
    action_uuid = generate_uuid("action")

    try:
        save_to_sqlite({
            "uuid": action_uuid,
            "action_type": action_type,
            "term": term or "",
            "note_path": note_path or "",
            "details": json.dumps(details or {}),
            "reversible": 1 if reversible else 0,
            "undone": 0,
            "created_at": datetime.now().isoformat()
        }, "action_log")
    except Exception:
        pass

    return action_uuid


def get_action_log(limit: int = 50, note_path: str = None) -> List[Dict]:
    """
    Get recent actions (running list).

    Args:
        limit: Max actions to return
        note_path: Filter by paper (optional)

    Returns:
        List of recent actions
    """
    try:
        if note_path:
            actions = get_from_sqlite('''
                SELECT * FROM action_log
                WHERE note_path = ?
                ORDER BY created_at DESC
                LIMIT ?
            ''', [note_path, limit])
        else:
            actions = get_from_sqlite('''
                SELECT * FROM action_log
                ORDER BY created_at DESC
                LIMIT ?
            ''', [limit])

        result = []
        for a in actions:
            action = dict(a)
            action['details'] = json.loads(action.get('details', '{}'))
            action['can_undo'] = action.get('reversible', 0) == 1 and action.get('undone', 0) == 0
            result.append(action)

        return result

    except Exception:
        return []


def undo_action(action_uuid: str) -> Dict[str, Any]:
    """
    Undo a specific action.

    Args:
        action_uuid: Action to undo

    Returns:
        Result of undo operation
    """
    result = {
        "success": False,
        "action_uuid": action_uuid,
        "message": ""
    }

    try:
        # Get the action
        actions = get_from_sqlite(
            "SELECT * FROM action_log WHERE uuid = ? LIMIT 1",
            [action_uuid]
        )

        if not actions:
            result["message"] = "Action not found"
            return result

        action = actions[0]

        if action['undone'] == 1:
            result["message"] = "Action already undone"
            return result

        if action['reversible'] != 1:
            result["message"] = "Action cannot be undone"
            return result

        # Perform undo based on action type
        action_type = action['action_type']
        details = json.loads(action.get('details', '{}'))

        if action_type == 'link_added':
            # Remove the link from the note
            success = remove_link_from_note(
                action['note_path'],
                action['term']
            )
            result["success"] = success
            result["message"] = "Link removed" if success else "Failed to remove link"

        elif action_type == 'definition_created':
            # Delete the definition file
            file_path = details.get('file_path')
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
                result["success"] = True
                result["message"] = "Definition file deleted"

        elif action_type == 'term_disabled':
            # Re-enable the term
            enable_term(action['term'], action['note_path'] or None)
            result["success"] = True
            result["message"] = "Term re-enabled"

        # Mark action as undone
        if result["success"]:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE action_log SET undone = 1 WHERE uuid = ?",
                [action_uuid]
            )
            conn.commit()
            conn.close()

    except Exception as e:
        result["message"] = str(e)

    return result


def remove_link_from_note(note_path: str, term: str) -> bool:
    """
    Remove a wiki-link for a term from a note.

    Args:
        note_path: Path to note
        term: Term to unlink

    Returns:
        True if successful
    """
    import re

    try:
        with open(note_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Remove [[term]] or [[something|term]]
        pattern = rf'\[\[(?:[^\]|]+\|)?({re.escape(term)})\]\]'
        new_content = re.sub(pattern, r'\1', content, flags=re.IGNORECASE)

        if new_content != content:
            with open(note_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return True

        return False

    except Exception:
        return False


def clear_action_log(older_than_days: int = 30) -> int:
    """
    Clear old actions from the log.

    Args:
        older_than_days: Delete actions older than this

    Returns:
        Number of actions deleted
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM action_log
            WHERE created_at < datetime('now', ?)
        ''', [f'-{older_than_days} days'])
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        return deleted
    except Exception:
        return 0


# ============================================
# MULTI-SOURCE LINKS (Glossary + Stanford + Wiki)
# ============================================

def get_multi_source_link_data(term: str, vault_path: str) -> Dict[str, Any]:
    """
    Get all available sources for a term (for hover popup).

    This is what shows when user hovers over a linked term.

    Args:
        term: The term
        vault_path: Vault path

    Returns:
        Data for multi-source popup

    Example return:
        {
            "term": "Einstein",
            "sources": [
                {
                    "name": "Glossary",
                    "type": "local",
                    "path": "/vault/Definitions/einstein.md",
                    "preview": "Albert Einstein was a theoretical physicist..."
                },
                {
                    "name": "Stanford Encyclopedia",
                    "type": "external",
                    "url": "https://plato.stanford.edu/...",
                    "preview": "Einstein's contributions to physics..."
                },
                {
                    "name": "Wikipedia",
                    "type": "external",
                    "url": "https://en.wikipedia.org/wiki/Einstein",
                    "preview": "Albert Einstein was a German-born..."
                }
            ]
        }
    """
    result = {
        "term": term,
        "sources": []
    }

    # 1. Check local glossary
    def_file = os.path.join(vault_path, "Definitions", f"{term.lower().replace(' ', '_')}.md")
    if os.path.exists(def_file):
        try:
            with open(def_file, 'r', encoding='utf-8') as f:
                content = f.read()
            # Get preview (first 200 chars after ## Summary)
            import re
            summary_match = re.search(r'## Summary\n\n(.+?)(?=\n##|\n---|\Z)', content, re.DOTALL)
            preview = summary_match.group(1)[:200] + "..." if summary_match else content[:200] + "..."

            result["sources"].append({
                "name": "Glossary",
                "type": "local",
                "path": def_file,
                "preview": preview.strip()
            })
        except Exception:
            pass

    # 2. Check database for external sources
    try:
        cached = get_from_sqlite(
            "SELECT * FROM definitions WHERE term = ?",
            [term.lower()]
        )

        for c in cached:
            if c['source'] == 'stanford':
                result["sources"].append({
                    "name": "Stanford Encyclopedia",
                    "type": "external",
                    "url": c['source_url'],
                    "preview": c['short_definition'][:200] + "..." if len(c['short_definition']) > 200 else c['short_definition']
                })
            elif c['source'] == 'wikipedia':
                result["sources"].append({
                    "name": "Wikipedia",
                    "type": "external",
                    "url": c['source_url'],
                    "preview": c['short_definition'][:200] + "..." if len(c['short_definition']) > 200 else c['short_definition']
                })
    except Exception:
        pass

    # 3. Always add potential external links even if not cached
    if not any(s['name'] == 'Wikipedia' for s in result["sources"]):
        result["sources"].append({
            "name": "Wikipedia",
            "type": "external",
            "url": f"https://en.wikipedia.org/wiki/{term.replace(' ', '_')}",
            "preview": "Click to view on Wikipedia",
            "not_fetched": True
        })

    if not any(s['name'] == 'Stanford Encyclopedia' for s in result["sources"]):
        result["sources"].append({
            "name": "Stanford Encyclopedia",
            "type": "external",
            "url": f"https://plato.stanford.edu/search/searcher.py?query={term.replace(' ', '+')}",
            "preview": "Search Stanford Encyclopedia",
            "not_fetched": True
        })

    return result
