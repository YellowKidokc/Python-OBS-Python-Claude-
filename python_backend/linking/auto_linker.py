"""
Auto Linker

Automatically creates links in notes to definitions.

For beginners:
- Scans a note for terms
- Checks if we have definitions for them
- Adds [[wiki-style links]] to the note
- Can link ALL occurrences (not just first)
- Respects disabled terms/papers
- Logs all actions for undo
"""

import os
import re
from typing import List, Dict, Any, Set

from linking.term_finder import find_terms
from linking.definition_lookup import lookup_definition


def auto_link_note(
    note_path: str,
    vault_path: str = None,
    link_all: bool = True,
    respect_settings: bool = True
) -> Dict[str, Any]:
    """
    Automatically link terms in a note.

    Args:
        note_path: Path to the markdown file
        vault_path: Path to Obsidian vault
        link_all: If True, link ALL occurrences. If False, just first.
        respect_settings: Check disabled terms/papers

    Returns:
        Summary of what was linked

    Example:
        result = auto_link_note("/vault/notes/physics.md", "/vault", link_all=True)
        # Returns:
        # {
        #     "linked": [
        #         {"term": "Einstein", "count": 5},
        #         {"term": "relativity", "count": 3}
        #     ],
        #     "not_found": ["some term"],
        #     "already_linked": ["gravity"],
        #     "skipped": [{"term": "the", "reason": "disabled"}]
        # }
    """
    from linking.link_preview import get_link_settings, log_action

    # Read the note
    with open(note_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content  # Keep for comparison

    # Find terms
    terms = find_terms(note_path)

    result = {
        "linked": [],
        "not_found": [],
        "already_linked": [],
        "skipped": [],
        "actions": []  # UUIDs for undo
    }

    # Get settings if respecting them
    settings = get_link_settings() if respect_settings else None

    # Check if paper is disabled
    if settings and note_path in settings.get("disabled_papers", []):
        result["skipped"].append({
            "term": "*all*",
            "reason": "paper_disabled"
        })
        return result

    # Process each term
    for term_data in terms:
        term = term_data['term']
        term_lower = term.lower()
        occurrences = term_data.get('count', 1)

        # Check if term is disabled globally
        if settings and term_lower in settings.get("disabled_terms", []):
            result["skipped"].append({
                "term": term,
                "reason": "disabled_globally"
            })
            continue

        # Check if term is disabled for this paper
        if settings:
            paper_disabled = [p for p in settings.get("paper_disabled_terms", [])
                            if p['term'] == term_lower and p['paper'] == note_path]
            if paper_disabled:
                result["skipped"].append({
                    "term": term,
                    "reason": "disabled_for_paper"
                })
                continue

        # Count existing links
        existing_links = count_existing_links(content, term)

        # Skip if ALL occurrences already linked
        if existing_links >= occurrences:
            result["already_linked"].append({
                "term": term,
                "count": existing_links
            })
            continue

        # Check if we have a definition
        definition = lookup_definition(term, vault_path, create_file=False)

        if definition:
            # Add links
            if link_all:
                content, links_added = add_all_links(content, term)
            else:
                content, links_added = add_single_link(content, term)

            if links_added > 0:
                result["linked"].append({
                    "term": term,
                    "count": links_added
                })

                # Log action for undo
                action_uuid = log_action(
                    action_type="link_added",
                    term=term,
                    note_path=note_path,
                    details={"count": links_added, "link_all": link_all},
                    reversible=True
                )
                result["actions"].append(action_uuid)
        else:
            result["not_found"].append(term)

    # Save updated content if changed
    if content != original_content:
        with open(note_path, 'w', encoding='utf-8') as f:
            f.write(content)

    return result


def count_existing_links(content: str, term: str) -> int:
    """
    Count how many times a term is already linked.

    Args:
        content: Note text
        term: Term to count

    Returns:
        Number of existing links
    """
    pattern = rf'\[\[{re.escape(term)}(?:\|[^\]]+)?\]\]'
    matches = re.findall(pattern, content, re.IGNORECASE)
    return len(matches)


def is_already_linked(content: str, term: str) -> bool:
    """
    Check if a term is already linked (at least once).

    Args:
        content: Note text
        term: Term to check

    Returns:
        True if already linked
    """
    return count_existing_links(content, term) > 0


def add_single_link(content: str, term: str) -> tuple:
    """
    Add wiki-style link to FIRST occurrence of a term.

    Args:
        content: Note text
        term: Term to link

    Returns:
        Tuple of (updated_content, links_added_count)
    """
    # Mark unsafe zones (code blocks, existing links, etc.)
    protected_content = mark_unsafe_zones(content)

    # Find first safe occurrence
    pattern = rf'\b{re.escape(term)}\b'
    match = re.search(pattern, protected_content, re.IGNORECASE)

    if match:
        start, end = match.span()
        # Check if this position is in a safe zone
        if protected_content[start:end] == content[start:end]:
            original_term = content[start:end]
            linked = f'[[{original_term}]]'
            content = content[:start] + linked + content[end:]
            return content, 1

    return content, 0


def add_all_links(content: str, term: str) -> tuple:
    """
    Add wiki-style links to ALL occurrences of a term.

    Args:
        content: Note text
        term: Term to link

    Returns:
        Tuple of (updated_content, links_added_count)
    """
    # Mark unsafe zones
    protected_content = mark_unsafe_zones(content)

    links_added = 0

    # Find all occurrences (working backwards to preserve positions)
    pattern = rf'\b{re.escape(term)}\b'
    matches = list(re.finditer(pattern, protected_content, re.IGNORECASE))

    # Process in reverse order so positions don't shift
    for match in reversed(matches):
        start, end = match.span()

        # Check if this position is safe (not in code block, not already linked, etc.)
        if protected_content[start:end] == content[start:end]:
            # Check it's not already linked
            before = content[max(0, start-2):start]
            after = content[end:end+2]

            if before != '[[' and after != ']]':
                original_term = content[start:end]
                linked = f'[[{original_term}]]'
                content = content[:start] + linked + content[end:]
                links_added += 1

    return content, links_added


def mark_unsafe_zones(content: str) -> str:
    """
    Replace unsafe zones with null characters to prevent linking inside them.

    Unsafe zones:
    - Code blocks (```)
    - Inline code (`)
    - Existing wiki links [[]]
    - Markdown links []()
    - Tag blocks (%%)
    - URLs
    - YAML frontmatter

    Args:
        content: Original content

    Returns:
        Content with unsafe zones marked
    """
    protected = content

    unsafe_patterns = [
        r'```[\s\S]*?```',           # Code blocks
        r'`[^`]+`',                   # Inline code
        r'\[\[[^\]]+\]\]',            # Wiki links
        r'\[[^\]]+\]\([^)]+\)',       # Markdown links
        r'%%[^%]+%%',                 # Tag blocks
        r'https?://[^\s\)]+',         # URLs
        r'^---[\s\S]*?---',           # YAML frontmatter
    ]

    for pattern in unsafe_patterns:
        protected = re.sub(pattern, lambda m: '\x00' * len(m.group()), protected, flags=re.MULTILINE)

    return protected


def link_all_occurrences(content: str, term: str) -> str:
    """
    Link ALL occurrences of a term (legacy function for compatibility).

    Args:
        content: Note text
        term: Term to link

    Returns:
        Updated content
    """
    content, _ = add_all_links(content, term)
    return content


def batch_auto_link(
    folder_path: str,
    vault_path: str = None,
    link_all: bool = True
) -> Dict[str, Any]:
    """
    Auto-link all notes in a folder.

    Args:
        folder_path: Folder containing notes
        vault_path: Vault path
        link_all: Link all occurrences?

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
            note_result = auto_link_note(note_path, vault_path, link_all=link_all)

            results["notes"][filename] = note_result
            results["processed"] += 1
            results["total_linked"] += sum(t['count'] for t in note_result["linked"])
            results["total_not_found"] += len(note_result["not_found"])

    return results


def unlink_term(content: str, term: str, unlink_all: bool = True) -> tuple:
    """
    Remove links from a term.

    Args:
        content: Note text
        term: Term to unlink
        unlink_all: Remove all links or just first?

    Returns:
        Tuple of (updated_content, links_removed_count)
    """
    pattern = rf'\[\[(?:[^\]|]+\|)?({re.escape(term)})\]\]'

    if unlink_all:
        new_content = re.sub(pattern, r'\1', content, flags=re.IGNORECASE)
        removed = len(re.findall(pattern, content, re.IGNORECASE))
    else:
        new_content = re.sub(pattern, r'\1', content, count=1, flags=re.IGNORECASE)
        removed = 1 if new_content != content else 0

    return new_content, removed


def unlink_term_from_note(note_path: str, term: str, unlink_all: bool = True) -> Dict[str, Any]:
    """
    Remove links for a term from a note file.

    Args:
        note_path: Path to note
        term: Term to unlink
        unlink_all: Remove all or just first?

    Returns:
        Result summary
    """
    with open(note_path, 'r', encoding='utf-8') as f:
        content = f.read()

    new_content, removed = unlink_term(content, term, unlink_all)

    if removed > 0:
        with open(note_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

    return {
        "term": term,
        "note_path": note_path,
        "links_removed": removed
    }


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

    # Count occurrences of each link
    link_counts = {}
    for link in links:
        link_counts[link] = link_counts.get(link, 0) + 1

    # Find all terms
    terms = find_terms(note_path)

    return {
        "total_links": len(links),
        "unique_links": len(set(links)),
        "links": link_counts,
        "potential_terms": [t['term'] for t in terms],
        "unlinked_terms": [
            t['term'] for t in terms
            if t['term'].lower() not in [l.lower() for l in links]
        ]
    }


def get_term_link_count(note_path: str, term: str) -> int:
    """
    Get how many times a specific term is linked in a note.

    Args:
        note_path: Path to note
        term: Term to count

    Returns:
        Number of links
    """
    with open(note_path, 'r', encoding='utf-8') as f:
        content = f.read()

    return count_existing_links(content, term)
