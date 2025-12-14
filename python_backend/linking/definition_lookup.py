"""
Definition Lookup

Looks up definitions from local files and external sources.

For beginners:
- First checks your local Definitions folder
- Then checks cached definitions in SQLite
- Then tries Stanford Encyclopedia of Philosophy
- Then tries Wikipedia
- Saves new definitions for future use

Priority order:
1. Local files (you control these)
2. SQLite cache (previously fetched)
3. Stanford (academic, trusted)
4. Other academic sources
5. Wikipedia (comprehensive but lower priority)
"""

import os
import re
import json
from typing import Optional, Dict, Any


# Path to definitions folder (relative to vault)
DEFINITIONS_FOLDER = "Definitions"


def lookup_definition(term: str, vault_path: str = None) -> Optional[Dict[str, Any]]:
    """
    Look up a definition using the priority chain.

    Args:
        term: Word or phrase to define
        vault_path: Path to Obsidian vault (for local lookup)

    Returns:
        Definition data or None if not found

    Example:
        result = lookup_definition("entropy", "/vault")
        # Returns:
        # {
        #     "term": "entropy",
        #     "short_definition": "A measure of disorder...",
        #     "source": "local",
        #     "source_url": None,
        #     "file_path": "/vault/Definitions/entropy.md"
        # }
    """
    # Try each source in order

    # 1. Local definitions folder
    result = lookup_local(term, vault_path)
    if result:
        return result

    # 2. SQLite cache
    result = lookup_cache(term)
    if result:
        return result

    # 3. Stanford Encyclopedia
    result = lookup_stanford(term)
    if result:
        # Cache it for next time
        cache_definition(term, result)
        return result

    # 4. Wikipedia
    result = lookup_wikipedia(term)
    if result:
        cache_definition(term, result)
        return result

    return None


def lookup_local(term: str, vault_path: str = None) -> Optional[Dict[str, Any]]:
    """
    Check the local Definitions folder.

    Args:
        term: Word to find
        vault_path: Vault location

    Returns:
        Definition if found locally
    """
    if not vault_path:
        return None

    # Convert term to filename (lowercase, spaces to underscores)
    filename = term.lower().replace(' ', '_') + '.md'
    file_path = os.path.join(vault_path, DEFINITIONS_FOLDER, filename)

    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        return parse_definition_file(term, content, file_path)

    # Also try with original case
    filename = term.replace(' ', '_') + '.md'
    file_path = os.path.join(vault_path, DEFINITIONS_FOLDER, filename)

    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        return parse_definition_file(term, content, file_path)

    return None


def parse_definition_file(term: str, content: str, file_path: str) -> Dict[str, Any]:
    """
    Parse a definition markdown file.

    Expected format:
    # Term

    ## Short Definition
    Brief explanation...

    ## Long Definition
    Detailed explanation...

    ## Source
    Where this came from
    """
    result = {
        "term": term,
        "short_definition": "",
        "long_definition": "",
        "source": "local",
        "source_url": None,
        "file_path": file_path
    }

    # Extract sections
    sections = re.split(r'^## ', content, flags=re.MULTILINE)

    for section in sections:
        if section.lower().startswith('short definition'):
            lines = section.split('\n', 1)
            if len(lines) > 1:
                result["short_definition"] = lines[1].strip()

        elif section.lower().startswith('long definition'):
            lines = section.split('\n', 1)
            if len(lines) > 1:
                result["long_definition"] = lines[1].strip()

        elif section.lower().startswith('source'):
            lines = section.split('\n', 1)
            if len(lines) > 1:
                # Try to extract URL
                url_match = re.search(r'https?://[^\s]+', lines[1])
                if url_match:
                    result["source_url"] = url_match.group()

    return result


def lookup_cache(term: str) -> Optional[Dict[str, Any]]:
    """
    Check SQLite cache for a definition.

    Args:
        term: Word to find

    Returns:
        Cached definition if found
    """
    # Import here to avoid circular imports
    try:
        from database.sqlite_db import get_from_sqlite

        result = get_from_sqlite(
            "SELECT * FROM definitions WHERE term = ? LIMIT 1",
            [term.lower()]
        )

        if result:
            return {
                "term": result[0]['term'],
                "short_definition": result[0]['short_definition'],
                "source": result[0]['source'],
                "source_url": result[0].get('source_url'),
                "cached": True
            }
    except Exception:
        pass

    return None


def lookup_stanford(term: str) -> Optional[Dict[str, Any]]:
    """
    Look up term in Stanford Encyclopedia of Philosophy.

    Args:
        term: Word to find

    Returns:
        Definition if found

    Note: This requires internet access and the requests library.
    """
    # TODO: Implement actual Stanford API call
    # For now, return None (not implemented)
    #
    # Real implementation would:
    # 1. Query Stanford's API or search
    # 2. Parse the response
    # 3. Extract definition and source URL
    #
    # Example:
    # import requests
    # url = f"https://plato.stanford.edu/search/searcher.py?query={term}"
    # response = requests.get(url)
    # ... parse response ...

    return None


def lookup_wikipedia(term: str) -> Optional[Dict[str, Any]]:
    """
    Look up term in Wikipedia.

    Args:
        term: Word to find

    Returns:
        Definition if found

    Note: This requires internet access and the requests library.
    """
    # TODO: Implement actual Wikipedia API call
    # For now, return None (not implemented)
    #
    # Real implementation would use Wikipedia's API:
    # https://en.wikipedia.org/api/rest_v1/page/summary/{term}
    #
    # Example:
    # import requests
    # url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{term}"
    # response = requests.get(url)
    # data = response.json()
    # return {
    #     "term": term,
    #     "short_definition": data.get("extract"),
    #     "source": "wikipedia",
    #     "source_url": data.get("content_urls", {}).get("desktop", {}).get("page")
    # }

    return None


def cache_definition(term: str, definition: Dict[str, Any]) -> bool:
    """
    Save a definition to SQLite cache.

    Args:
        term: The term
        definition: Definition data

    Returns:
        True if cached successfully
    """
    try:
        from database.sqlite_db import save_to_sqlite

        save_to_sqlite({
            "term": term.lower(),
            "short_definition": definition.get("short_definition", ""),
            "long_definition": definition.get("long_definition", ""),
            "source": definition.get("source", "unknown"),
            "source_url": definition.get("source_url", "")
        }, "definitions")

        return True
    except Exception:
        return False


def create_definition_file(
    term: str,
    definition: Dict[str, Any],
    vault_path: str
) -> str:
    """
    Create a new definition file in the vault.

    Args:
        term: The term being defined
        definition: Definition data
        vault_path: Path to Obsidian vault

    Returns:
        Path to created file

    Example:
        path = create_definition_file(
            "entropy",
            {"short_definition": "Measure of disorder..."},
            "/vault"
        )
        # Creates /vault/Definitions/entropy.md
    """
    # Ensure definitions folder exists
    def_folder = os.path.join(vault_path, DEFINITIONS_FOLDER)
    if not os.path.exists(def_folder):
        os.makedirs(def_folder)

    # Create filename
    filename = term.lower().replace(' ', '_') + '.md'
    file_path = os.path.join(def_folder, filename)

    # Build content
    content = f"""# {term}

## Short Definition
{definition.get('short_definition', 'No definition available.')}

## Long Definition
{definition.get('long_definition', '')}

## Source
{definition.get('source', 'Unknown')}
{definition.get('source_url', '')}

## Related Terms
<!-- Add related terms here -->

## Tags
- definition

## Metadata
Created: {__import__('datetime').datetime.now().isoformat()}
Source Type: {definition.get('source', 'Unknown')}
"""

    # Write file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    return file_path
