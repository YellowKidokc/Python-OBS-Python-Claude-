"""
Semantic Tree Builder

Builds hierarchical structures from notes:
Note → Paragraphs → Sentences → Terms

For beginners:
- A "semantic tree" shows the structure of a document
- Each level (note, paragraph, sentence) gets a UUID
- Tags attach to specific levels
- This helps us know exactly what a tag refers to
"""

import re
from typing import Dict, Any, List

from tags.uuid_manager import generate_uuid


def build_semantic_tree(note_path: str) -> Dict[str, Any]:
    """
    Build a semantic tree from a note.

    Args:
        note_path: Path to the markdown file

    Returns:
        Tree structure with UUIDs

    Example output:
        {
            "uuid": "note-abc123",
            "level": "note",
            "title": "Physics Basics",
            "children": [
                {
                    "uuid": "para-def456",
                    "level": "paragraph",
                    "position": 1,
                    "children": [
                        {
                            "uuid": "sent-ghi789",
                            "level": "sentence",
                            "content": "Light travels at 299,792 km/s.",
                            "terms": ["Light"]
                        }
                    ]
                }
            ]
        }
    """
    with open(note_path, 'r', encoding='utf-8') as f:
        content = f.read()

    return build_tree_from_content(content, note_path)


def build_tree_from_content(content: str, source_path: str = None) -> Dict[str, Any]:
    """
    Build tree from content string.

    Args:
        content: The note text
        source_path: Optional path for title extraction

    Returns:
        Tree structure
    """
    # Create note-level node
    note_uuid = generate_uuid('note')
    title = extract_title(content, source_path)

    tree = {
        "uuid": note_uuid,
        "level": "note",
        "title": title,
        "children": []
    }

    # Remove frontmatter and tag blocks
    clean_content = remove_metadata(content)

    # Split into paragraphs
    paragraphs = split_into_paragraphs(clean_content)

    for i, para_text in enumerate(paragraphs):
        if not para_text.strip():
            continue

        # Create paragraph node
        para_uuid = generate_uuid('para')
        para_node = {
            "uuid": para_uuid,
            "level": "paragraph",
            "position": i + 1,
            "parent_uuid": note_uuid,
            "children": []
        }

        # Split paragraph into sentences
        sentences = split_into_sentences(para_text)

        for j, sent_text in enumerate(sentences):
            if not sent_text.strip():
                continue

            # Create sentence node
            sent_uuid = generate_uuid('sent')
            terms = extract_terms(sent_text)

            sent_node = {
                "uuid": sent_uuid,
                "level": "sentence",
                "position": j + 1,
                "parent_uuid": para_uuid,
                "content": sent_text.strip(),
                "terms": terms
            }

            para_node["children"].append(sent_node)

        tree["children"].append(para_node)

    return tree


def extract_title(content: str, path: str = None) -> str:
    """
    Extract the title from content or path.

    Args:
        content: Note text
        path: File path

    Returns:
        Title string
    """
    # Try to find H1 header
    match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if match:
        return match.group(1).strip()

    # Try frontmatter title
    fm_match = re.search(r'^title:\s*(.+)$', content, re.MULTILINE)
    if fm_match:
        return fm_match.group(1).strip()

    # Fall back to filename
    if path:
        import os
        filename = os.path.basename(path)
        return filename.replace('.md', '').replace('_', ' ')

    return "Untitled"


def remove_metadata(content: str) -> str:
    """
    Remove frontmatter and tag blocks.

    Args:
        content: Raw note text

    Returns:
        Clean content
    """
    # Remove YAML frontmatter
    content = re.sub(r'^---[\s\S]*?---\n?', '', content)

    # Remove tag blocks
    content = re.sub(r'%%[^%]+%%', '', content)

    # Remove the semantic tags comment
    content = re.sub(r'<!-- Semantic Tags.*?-->\n?', '', content)

    return content


def split_into_paragraphs(content: str) -> List[str]:
    """
    Split content into paragraphs.

    Args:
        content: Clean text

    Returns:
        List of paragraph strings
    """
    # Split on double newlines
    paragraphs = re.split(r'\n\s*\n', content)
    return [p.strip() for p in paragraphs if p.strip()]


def split_into_sentences(text: str) -> List[str]:
    """
    Split text into sentences.

    Args:
        text: Paragraph text

    Returns:
        List of sentences
    """
    # Simple sentence splitter
    # Handles: . ! ? followed by space and capital letter
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
    return sentences


def extract_terms(text: str) -> List[str]:
    """
    Extract potential terms from a sentence.

    Args:
        text: Sentence text

    Returns:
        List of terms found
    """
    terms = []

    # Find capitalized words (not at start)
    words = text.split()
    for i, word in enumerate(words):
        clean = re.sub(r'[^\w]', '', word)
        if clean and clean[0].isupper():
            # Skip if it's the first word (sentence start)
            if i > 0:
                terms.append(clean)

    return terms


def flatten_tree(tree: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Flatten a tree into a list of nodes.

    Useful for database storage.

    Args:
        tree: Hierarchical tree

    Returns:
        Flat list of nodes

    Example:
        nodes = flatten_tree(tree)
        for node in nodes:
            save_to_database(node)
    """
    nodes = []

    def traverse(node, parent_uuid=None):
        flat = {
            "uuid": node["uuid"],
            "level": node["level"],
            "parent_uuid": parent_uuid,
            "position": node.get("position"),
            "content": node.get("content"),
            "title": node.get("title"),
            "terms": node.get("terms", [])
        }
        nodes.append(flat)

        for child in node.get("children", []):
            traverse(child, node["uuid"])

    traverse(tree)
    return nodes


def get_node_by_uuid(tree: Dict[str, Any], uuid: str) -> Dict[str, Any]:
    """
    Find a node in the tree by UUID.

    Args:
        tree: The tree to search
        uuid: UUID to find

    Returns:
        Node if found, None otherwise
    """
    if tree["uuid"] == uuid:
        return tree

    for child in tree.get("children", []):
        result = get_node_by_uuid(child, uuid)
        if result:
            return result

    return None


def get_path_to_node(tree: Dict[str, Any], uuid: str) -> List[str]:
    """
    Get the path from root to a node.

    Args:
        tree: The tree
        uuid: Target node UUID

    Returns:
        List of UUIDs from root to target
    """
    def find_path(node, target, path):
        path = path + [node["uuid"]]

        if node["uuid"] == target:
            return path

        for child in node.get("children", []):
            result = find_path(child, target, path)
            if result:
                return result

        return None

    return find_path(tree, uuid, []) or []
