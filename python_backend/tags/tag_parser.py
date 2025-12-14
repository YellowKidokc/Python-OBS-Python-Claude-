"""
Tag Parser

Reads and parses tag blocks from markdown notes.

For beginners:
- This reads the %%tag::...%% blocks from notes
- Converts them back into Python dictionaries
- Used for analysis, display, and syncing
"""

import re
from typing import List, Dict, Any, Optional


def parse_tags(note_path: str) -> List[Dict[str, Any]]:
    """
    Read a note and extract all tag blocks.

    Args:
        note_path: Path to the markdown file

    Returns:
        List of tag dictionaries

    Example:
        tags = parse_tags("/vault/notes/physics.md")
        # Returns:
        # [
        #     {"type": "Axiom", "uuid": "ax-123", "content": "Space is curved"},
        #     {"type": "Claim", "uuid": "cl-456", "content": "Light bends"}
        # ]
    """
    with open(note_path, 'r', encoding='utf-8') as f:
        content = f.read()

    return parse_tags_from_content(content)


def parse_tags_from_content(content: str) -> List[Dict[str, Any]]:
    """
    Extract tags from content string.

    Args:
        content: The note text

    Returns:
        List of tag dictionaries
    """
    tags = []

    # Pattern to match tag blocks
    # %%tag::Type::UUID::"Content"::ParentUUID%%
    # or %%tag::Type::UUID::"Content"%%
    pattern = r'%%tag::([^:]+)::([^:]+)::"([^"]+)"(?:::([^%]+))?%%'

    matches = re.findall(pattern, content)

    for match in matches:
        tag_type, uuid, tag_content, parent_uuid = match

        tag = {
            "type": tag_type,
            "uuid": uuid,
            "content": tag_content.replace('\\"', '"')  # Unescape quotes
        }

        if parent_uuid:
            tag["parent_uuid"] = parent_uuid

        tags.append(tag)

    return tags


def get_tags_by_type(note_path: str, tag_type: str) -> List[Dict[str, Any]]:
    """
    Get only tags of a specific type.

    Args:
        note_path: Path to the note
        tag_type: "Axiom", "Claim", "Evidence", etc.

    Returns:
        Filtered list of tags

    Example:
        axioms = get_tags_by_type("/vault/notes/physics.md", "Axiom")
    """
    all_tags = parse_tags(note_path)
    return [t for t in all_tags if t['type'].lower() == tag_type.lower()]


def get_tag_by_uuid(note_path: str, uuid: str) -> Optional[Dict[str, Any]]:
    """
    Find a specific tag by UUID.

    Args:
        note_path: Path to the note
        uuid: UUID to search for

    Returns:
        The tag if found, None otherwise
    """
    all_tags = parse_tags(note_path)
    for tag in all_tags:
        if tag['uuid'] == uuid:
            return tag
    return None


def count_tags(note_path: str) -> Dict[str, int]:
    """
    Count tags by type.

    Args:
        note_path: Path to the note

    Returns:
        Dictionary of type -> count

    Example:
        counts = count_tags("/vault/notes/physics.md")
        # Returns: {"Axiom": 2, "Claim": 5, "Evidence": 3}
    """
    all_tags = parse_tags(note_path)
    counts = {}

    for tag in all_tags:
        tag_type = tag['type']
        counts[tag_type] = counts.get(tag_type, 0) + 1

    return counts


def has_tags(note_path: str) -> bool:
    """
    Check if a note has any tags.

    Args:
        note_path: Path to the note

    Returns:
        True if note has tags
    """
    with open(note_path, 'r', encoding='utf-8') as f:
        content = f.read()

    return '%%tag::' in content


def extract_tag_content_only(note_path: str) -> List[str]:
    """
    Get just the content strings from all tags.

    Useful for analysis without the metadata.

    Args:
        note_path: Path to the note

    Returns:
        List of content strings

    Example:
        contents = extract_tag_content_only("/vault/notes/physics.md")
        # Returns: ["Space is curved", "Light bends", ...]
    """
    all_tags = parse_tags(note_path)
    return [tag['content'] for tag in all_tags]


def find_tags_with_parent(note_path: str, parent_uuid: str) -> List[Dict[str, Any]]:
    """
    Find all tags that belong to a specific parent.

    Args:
        note_path: Path to the note
        parent_uuid: Parent UUID to search for

    Returns:
        List of child tags
    """
    all_tags = parse_tags(note_path)
    return [t for t in all_tags if t.get('parent_uuid') == parent_uuid]


def parse_tag_line(line: str) -> Optional[Dict[str, Any]]:
    """
    Parse a single tag block line.

    Args:
        line: A string containing a tag block

    Returns:
        Tag dictionary or None if not a valid tag

    Example:
        tag = parse_tag_line('%%tag::Claim::cl-123::"Light bends"%%')
        # Returns: {"type": "Claim", "uuid": "cl-123", "content": "Light bends"}
    """
    if not line.strip().startswith('%%tag::'):
        return None

    pattern = r'%%tag::([^:]+)::([^:]+)::"([^"]+)"(?:::([^%]+))?%%'
    match = re.search(pattern, line)

    if not match:
        return None

    tag_type, uuid, content, parent_uuid = match.groups()

    tag = {
        "type": tag_type,
        "uuid": uuid,
        "content": content.replace('\\"', '"')
    }

    if parent_uuid:
        tag["parent_uuid"] = parent_uuid

    return tag
