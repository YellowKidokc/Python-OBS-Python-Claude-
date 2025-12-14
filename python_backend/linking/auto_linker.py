"""
Auto Linker

Automatically creates links in notes to definitions.

For beginners:
- Scans a note for terms
- Checks if we have definitions for them
- Adds [[wiki-style links]] to the note
- Can work on single notes or whole folders
"""

import os
import re
from typing import List, Dict, Any, Set

from linking.term_finder import find_terms
from linking.definition_lookup import lookup_definition


def auto_link_note(note_path: str, vault_path: str = None) -> Dict[str, Any]:
    """
    Automatically link terms in a note.

    Args:
        note_path: Path to the markdown file
        vault_path: Path to Obsidian vault

    Returns:
        Summary of what was linked

    Example:
        result = auto_link_note("/vault/notes/physics.md", "/vault")
        # Returns:
        # {
        #     "linked": ["Einstein", "relativity"],
        #     "not_found": ["some term"],
        #     "already_linked": ["gravity"]
        # }
    """
    # Read the note
    with open(note_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find terms
    terms = find_terms(note_path)

    result = {
        "linked": [],
        "not_found": [],
        "already_linked": [],
        "skipped": []
    }

    # Process each term
    for term_data in terms:
        term = term_data['term']

        # Skip if already linked
        if is_already_linked(content, term):
            result["already_linked"].append(term)
            continue

        # Check if we have a definition
        definition = lookup_definition(term, vault_path)

        if definition:
            # Add link
            content = add_link(content, term)
            result["linked"].append(term)
        else:
            result["not_found"].append(term)

    # Save updated content
    with open(note_path, 'w', encoding='utf-8') as f:
        f.write(content)

    return result


def is_already_linked(content: str, term: str) -> bool:
    """
    Check if a term is already linked.

    Args:
        content: Note text
        term: Term to check

    Returns:
        True if already linked
    """
    # Pattern for [[term]] or [[term|display]]
    pattern = rf'\[\[{re.escape(term)}(?:\|[^\]]+)?\]\]'
    return bool(re.search(pattern, content, re.IGNORECASE))


def add_link(content: str, term: str) -> str:
    """
    Add wiki-style links to a term in content.

    Only links the first occurrence to avoid cluttering.

    Args:
        content: Note text
        term: Term to link

    Returns:
        Updated content with links
    """
    # Find the first occurrence that's not already linked
    # Avoid linking inside code blocks, existing links, or tag blocks

    # Split content into "safe" and "unsafe" zones
    safe_zones = []
    unsafe_patterns = [
        (r'```[\s\S]*?```', 'code_block'),
        (r'`[^`]+`', 'inline_code'),
        (r'\[\[[^\]]+\]\]', 'wiki_link'),
        (r'\[[^\]]+\]\([^)]+\)', 'md_link'),
        (r'%%[^%]+%%', 'tag_block'),
    ]

    # Mark unsafe zones
    protected_content = content
    for pattern, zone_type in unsafe_patterns:
        protected_content = re.sub(pattern, lambda m: '\x00' * len(m.group()), protected_content)

    # Find first safe occurrence
    pattern = rf'\b{re.escape(term)}\b'
    match = re.search(pattern, protected_content, re.IGNORECASE)

    if match:
        start, end = match.span()
        original_term = content[start:end]  # Preserve original case
        linked = f'[[{original_term}]]'
        content = content[:start] + linked + content[end:]

    return content


def link_all_occurrences(content: str, term: str) -> str:
    """
    Link ALL occurrences of a term (not just first).

    Args:
        content: Note text
        term: Term to link

    Returns:
        Updated content
    """
    # Similar to add_link but replaces all

    # Find safe zones
    def replace_safe(match):
        return f'[[{match.group()}]]'

    # This is a simplified version - production code would
    # need to properly handle unsafe zones
    pattern = rf'(?<!\[\[)\b{re.escape(term)}\b(?!\]\])'
    content = re.sub(pattern, replace_safe, content, flags=re.IGNORECASE)

    return content


def batch_auto_link(folder_path: str, vault_path: str = None) -> Dict[str, Any]:
    """
    Auto-link all notes in a folder.

    Args:
        folder_path: Folder containing notes
        vault_path: Vault path

    Returns:
        Summary of all linking operations
    """
    results = {
        "processed": 0,
        "total_linked": 0,
        "total_not_found": 0,
        "notes": {}
    }

    for filename in os.listdir(folder_path):
        if filename.endswith('.md'):
            note_path = os.path.join(folder_path, filename)
            note_result = auto_link_note(note_path, vault_path)

            results["notes"][filename] = note_result
            results["processed"] += 1
            results["total_linked"] += len(note_result["linked"])
            results["total_not_found"] += len(note_result["not_found"])

    return results


def unlink_term(content: str, term: str) -> str:
    """
    Remove links from a term.

    Args:
        content: Note text
        term: Term to unlink

    Returns:
        Content with links removed
    """
    # Pattern for [[term]] or [[something|term]]
    pattern = rf'\[\[(?:[^\]|]+\|)?({re.escape(term)})\]\]'
    return re.sub(pattern, r'\1', content, flags=re.IGNORECASE)


def get_link_status(note_path: str) -> Dict[str, Any]:
    """
    Get linking status for a note.

    Args:
        note_path: Path to note

    Returns:
        Status information
    """
    with open(note_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find all wiki links
    links = re.findall(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]', content)

    # Find all terms
    terms = find_terms(note_path)

    return {
        "total_links": len(links),
        "unique_links": len(set(links)),
        "links": list(set(links)),
        "potential_terms": [t['term'] for t in terms],
        "unlinked_terms": [
            t['term'] for t in terms
            if t['term'] not in links
        ]
    }
