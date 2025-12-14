"""
Mermaid Diagram Generator

Creates Mermaid diagrams from tag data and semantic trees.

For beginners:
- Mermaid is a markdown-like language for diagrams
- It creates flowcharts, graphs, etc.
- Obsidian can render Mermaid natively
- We generate the code, plugin displays it
"""

from typing import List, Dict, Any


def generate_mermaid_diagram(
    tags: List[Dict[str, Any]],
    diagram_type: str = 'flowchart'
) -> str:
    """
    Generate Mermaid code from tag data.

    Args:
        tags: List of tag dictionaries
        diagram_type: 'flowchart', 'mindmap', or 'graph'

    Returns:
        Mermaid code string

    Example:
        tags = [
            {"type": "Axiom", "uuid": "ax-1", "content": "Space is curved"},
            {"type": "Claim", "uuid": "cl-1", "content": "Light bends", "parent_uuid": "ax-1"},
            {"type": "Evidence", "uuid": "ev-1", "content": "1919 eclipse", "parent_uuid": "cl-1"}
        ]
        mermaid = generate_mermaid_diagram(tags)

        # Output:
        # graph TD
        #     ax-1["Axiom: Space is curved"]
        #     cl-1["Claim: Light bends"]
        #     ev-1["Evidence: 1919 eclipse"]
        #     ax-1 --> cl-1
        #     cl-1 --> ev-1
    """
    if diagram_type == 'mindmap':
        return generate_mindmap(tags)
    elif diagram_type == 'graph':
        return generate_network_graph(tags)
    else:
        return generate_flowchart(tags)


def generate_flowchart(tags: List[Dict[str, Any]]) -> str:
    """
    Generate a top-down flowchart.

    Args:
        tags: Tag data

    Returns:
        Mermaid flowchart code
    """
    lines = ['graph TD']

    # Create node definitions
    for tag in tags:
        uuid = sanitize_id(tag['uuid'])
        tag_type = tag.get('type', 'Unknown')
        content = truncate_text(tag.get('content', ''), 40)

        # Style based on type
        style = get_node_style(tag_type)
        lines.append(f'    {uuid}{style[0]}"{tag_type}: {content}"{style[1]}')

    lines.append('')  # Empty line

    # Create connections
    connections = set()
    for tag in tags:
        if 'parent_uuid' in tag and tag['parent_uuid']:
            from_id = sanitize_id(tag['parent_uuid'])
            to_id = sanitize_id(tag['uuid'])
            connection = f'    {from_id} --> {to_id}'
            if connection not in connections:
                connections.add(connection)
                lines.append(connection)

    # If no parent relationships, try to connect by type hierarchy
    if not connections:
        lines.extend(generate_type_hierarchy(tags))

    return '\n'.join(lines)


def generate_mindmap(tags: List[Dict[str, Any]]) -> str:
    """
    Generate a mindmap.

    Args:
        tags: Tag data

    Returns:
        Mermaid mindmap code
    """
    lines = ['mindmap', '    root((Document))']

    # Group by type
    by_type = {}
    for tag in tags:
        tag_type = tag.get('type', 'Unknown')
        if tag_type not in by_type:
            by_type[tag_type] = []
        by_type[tag_type].append(tag)

    for tag_type, type_tags in by_type.items():
        lines.append(f'        {tag_type}')
        for tag in type_tags:
            content = truncate_text(tag.get('content', ''), 30)
            lines.append(f'            {content}')

    return '\n'.join(lines)


def generate_network_graph(tags: List[Dict[str, Any]]) -> str:
    """
    Generate a network graph (left-right layout).

    Args:
        tags: Tag data

    Returns:
        Mermaid graph code
    """
    lines = ['graph LR']

    for tag in tags:
        uuid = sanitize_id(tag['uuid'])
        tag_type = tag.get('type', 'Unknown')
        content = truncate_text(tag.get('content', ''), 30)

        shape = get_shape(tag_type)
        lines.append(f'    {uuid}{shape[0]}"{content}"{shape[1]}')

    # Add subgraph grouping by type
    by_type = {}
    for tag in tags:
        tag_type = tag.get('type', 'Unknown')
        if tag_type not in by_type:
            by_type[tag_type] = []
        by_type[tag_type].append(tag)

    for tag_type, type_tags in by_type.items():
        if len(type_tags) > 1:
            lines.append(f'    subgraph {tag_type}s')
            for tag in type_tags:
                lines.append(f'        {sanitize_id(tag["uuid"])}')
            lines.append('    end')

    return '\n'.join(lines)


def generate_type_hierarchy(tags: List[Dict[str, Any]]) -> List[str]:
    """
    Generate connections based on type hierarchy.

    Axiom → Claim → Evidence

    Args:
        tags: Tag data

    Returns:
        List of connection lines
    """
    lines = []
    hierarchy = ['Axiom', 'Claim', 'Evidence']

    # Group by type
    by_type = {}
    for tag in tags:
        tag_type = tag.get('type', 'Unknown')
        if tag_type not in by_type:
            by_type[tag_type] = []
        by_type[tag_type].append(tag)

    # Connect types in order
    for i in range(len(hierarchy) - 1):
        current_type = hierarchy[i]
        next_type = hierarchy[i + 1]

        if current_type in by_type and next_type in by_type:
            # Connect first of current to first of next
            from_id = sanitize_id(by_type[current_type][0]['uuid'])
            to_id = sanitize_id(by_type[next_type][0]['uuid'])
            lines.append(f'    {from_id} --> {to_id}')

    return lines


def generate_tree_diagram(tree: Dict[str, Any]) -> str:
    """
    Generate Mermaid from a semantic tree.

    Args:
        tree: Semantic tree from tree_builder

    Returns:
        Mermaid code
    """
    lines = ['graph TD']

    def process_node(node, parent_id=None):
        uuid = sanitize_id(node['uuid'])
        level = node.get('level', 'unknown')

        # Create label
        if level == 'note':
            label = node.get('title', 'Note')
            lines.append(f'    {uuid}["{label}"]')
        elif level == 'paragraph':
            label = f"Paragraph {node.get('position', '?')}"
            lines.append(f'    {uuid}("{label}")')
        elif level == 'sentence':
            content = truncate_text(node.get('content', ''), 30)
            lines.append(f'    {uuid}["{content}"]')

        # Add connection to parent
        if parent_id:
            lines.append(f'    {parent_id} --> {uuid}')

        # Process children
        for child in node.get('children', []):
            process_node(child, uuid)

    process_node(tree)
    return '\n'.join(lines)


def sanitize_id(uuid: str) -> str:
    """
    Make UUID safe for Mermaid.

    Args:
        uuid: Raw UUID

    Returns:
        Safe ID string
    """
    # Replace hyphens with underscores
    return uuid.replace('-', '_')


def truncate_text(text: str, max_length: int) -> str:
    """
    Truncate text for display.

    Args:
        text: Original text
        max_length: Maximum characters

    Returns:
        Truncated text
    """
    # Escape quotes
    text = text.replace('"', "'")

    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + '...'


def get_node_style(tag_type: str) -> tuple:
    """
    Get Mermaid node style based on tag type.

    Args:
        tag_type: Axiom, Claim, etc.

    Returns:
        Tuple of (open_bracket, close_bracket)
    """
    styles = {
        'Axiom': ('((', '))'),      # Circle
        'Claim': ('[[', ']]'),       # Subroutine
        'Evidence': ('[/', '/]'),    # Trapezoid
        'Definition': ('[(', ')]'),  # Stadium
        'Theory': ('{', '}'),        # Rhombus
    }
    return styles.get(tag_type, ('[', ']'))


def get_shape(tag_type: str) -> tuple:
    """
    Get shape markers for network graphs.
    """
    shapes = {
        'Axiom': ('([', '])'),
        'Claim': ('[[', ']]'),
        'Evidence': ('[/', '/]'),
    }
    return shapes.get(tag_type, ('[', ']'))


def generate_comparison_diagram(
    tags_a: List[Dict[str, Any]],
    tags_b: List[Dict[str, Any]],
    label_a: str = 'Document A',
    label_b: str = 'Document B'
) -> str:
    """
    Generate a side-by-side comparison diagram.

    Args:
        tags_a: Tags from first document
        tags_b: Tags from second document
        label_a: Label for first
        label_b: Label for second

    Returns:
        Mermaid code
    """
    lines = ['graph LR']

    # Subgraph for A
    lines.append(f'    subgraph {label_a}')
    for tag in tags_a:
        uuid = sanitize_id('a_' + tag['uuid'])
        content = truncate_text(tag.get('content', ''), 25)
        lines.append(f'        {uuid}["{content}"]')
    lines.append('    end')

    # Subgraph for B
    lines.append(f'    subgraph {label_b}')
    for tag in tags_b:
        uuid = sanitize_id('b_' + tag['uuid'])
        content = truncate_text(tag.get('content', ''), 25)
        lines.append(f'        {uuid}["{content}"]')
    lines.append('    end')

    return '\n'.join(lines)
