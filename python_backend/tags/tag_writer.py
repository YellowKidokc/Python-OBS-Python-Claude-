"""
Tag Writer

Writes tag blocks to markdown notes.

For beginners:
- Tags are stored at the bottom of notes
- They're wrapped in %% so Obsidian hides them
- Format: %%tag::Type::UUID::"Content"::ParentUUID%%
"""

import os
import re
from typing import List, Dict, Any


def format_tag_block(tag: Dict[str, Any]) -> str:
    """
    Convert a tag dictionary to a tag block string.

    Args:
        tag: Dictionary with:
            - type: "Axiom", "Claim", "Evidence", etc.
            - uuid: The tag's unique ID
            - content: The actual text
            - parent_uuid: (optional) What this belongs to

    Returns:
        Formatted tag block string

    Example:
        tag = {
            "type": "Claim",
            "uuid": "claim-abc12345",
            "content": "Light bends near mass",
            "parent_uuid": "sent-xyz78901"
        }
        result = format_tag_block(tag)
        # Returns: '%%tag::Claim::claim-abc12345::"Light bends near mass"::sent-xyz78901%%'
    """
    tag_type = tag.get('type', 'Unknown')
    tag_uuid = tag.get('uuid', '')
    content = tag.get('content', '')
    parent_uuid = tag.get('parent_uuid', '')

    # Escape any quotes in the content
    content = content.replace('"', '\\"')

    # Build the tag block
    parts = ['%%tag', tag_type, tag_uuid, f'"{content}"']

    if parent_uuid:
        parts.append(parent_uuid)

    return '::'.join(parts) + '%%'


def write_tag_blocks(tags: List[Dict[str, Any]], note_path: str) -> bool:
    """
    Write tag blocks to the bottom of a note.

    Args:
        tags: List of tag dictionaries
        note_path: Path to the markdown file

    Returns:
        True if successful

    Example:
        tags = [
            {"type": "Axiom", "uuid": "ax-123", "content": "Space is curved"},
            {"type": "Claim", "uuid": "cl-456", "content": "Time dilates"}
        ]
        write_tag_blocks(tags, "/vault/notes/physics.md")
    """
    if not tags:
        return True  # Nothing to write

    # Read existing note content
    with open(note_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Remove existing tag blocks (we'll rewrite them)
    content = remove_existing_tags(content)

    # Format all new tags
    tag_blocks = [format_tag_block(tag) for tag in tags]

    # Add separator and tags at the end
    new_content = content.rstrip() + '\n\n'
    new_content += '<!-- Semantic Tags (auto-generated) -->\n'
    new_content += '\n'.join(tag_blocks)
    new_content += '\n'

    # Write back
    with open(note_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return True


def remove_existing_tags(content: str) -> str:
    """
    Remove all existing tag blocks from content.

    Args:
        content: The note content

    Returns:
        Content without tag blocks
    """
    # Pattern to match tag blocks
    # Matches: %%tag::anything%%
    pattern = r'%%tag::[^%]+%%'

    # Remove tag blocks
    content = re.sub(pattern, '', content)

    # Remove the separator comment if present
    content = re.sub(r'<!-- Semantic Tags \(auto-generated\) -->\n?', '', content)

    # Clean up extra newlines at the end
    content = content.rstrip() + '\n'

    return content


def append_single_tag(tag: Dict[str, Any], note_path: str) -> bool:
    """
    Add a single tag to a note without removing existing ones.

    Args:
        tag: The tag to add
        note_path: Path to the note

    Returns:
        True if successful
    """
    with open(note_path, 'r', encoding='utf-8') as f:
        content = f.read()

    tag_block = format_tag_block(tag)

    # Check if we already have tags
    if '%%tag::' in content:
        # Add after the last tag
        content = content.rstrip() + '\n' + tag_block + '\n'
    else:
        # Add section header and tag
        content = content.rstrip() + '\n\n'
        content += '<!-- Semantic Tags (auto-generated) -->\n'
        content += tag_block + '\n'

    with open(note_path, 'w', encoding='utf-8') as f:
        f.write(content)

    return True


def update_tag(old_uuid: str, new_tag: Dict[str, Any], note_path: str) -> bool:
    """
    Update an existing tag by its UUID.

    Args:
        old_uuid: UUID of tag to update
        new_tag: New tag data
        note_path: Path to the note

    Returns:
        True if updated, False if not found
    """
    with open(note_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Pattern to find the specific tag
    pattern = rf'%%tag::[^:]+::{re.escape(old_uuid)}::[^%]+%%'

    new_block = format_tag_block(new_tag)

    if re.search(pattern, content):
        content = re.sub(pattern, new_block, content)
        with open(note_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True

    return False


def delete_tag(uuid: str, note_path: str) -> bool:
    """
    Remove a tag by its UUID.

    Args:
        uuid: UUID of tag to remove
        note_path: Path to the note

    Returns:
        True if deleted, False if not found
    """
    with open(note_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Pattern to find the specific tag
    pattern = rf'%%tag::[^:]+::{re.escape(uuid)}::[^%]+%%\n?'

    if re.search(pattern, content):
        content = re.sub(pattern, '', content)
        with open(note_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True

    return False
