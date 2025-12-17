"""
Definition Lookup

Looks up definitions from local files and external sources.
Fetches from Wikipedia and creates nicely formatted definition files.

For beginners:
- First checks your local Definitions folder
- Then checks cached definitions in SQLite
- Then tries Stanford Encyclopedia of Philosophy
- Then tries Wikipedia (with full section extraction)
- Saves new definitions for future use
- Creates a database entry for every link

Priority order:
1. Local files (you control these)
2. SQLite cache (previously fetched)
3. Stanford (academic, trusted)
4. Wikipedia (comprehensive, with sections)
"""

import os
import re
import json
from typing import Optional, Dict, Any, List
from datetime import datetime

# Try to import requests - needed for web lookups
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


# Path to definitions folder (relative to vault)
DEFINITIONS_FOLDER = "Definitions"


def lookup_definition(term: str, vault_path: str = None, create_file: bool = True) -> Optional[Dict[str, Any]]:
    """
    Look up a definition using the priority chain.
    If found online, automatically creates a local definition file.

    Args:
        term: Word or phrase to define
        vault_path: Path to Obsidian vault (for local lookup)
        create_file: Whether to create a definition file if found online

    Returns:
        Definition data or None if not found

    Example:
        result = lookup_definition("entropy", "/vault")
        # Returns:
        # {
        #     "term": "entropy",
        #     "short_definition": "A measure of disorder...",
        #     "source": "wikipedia",
        #     "source_url": "https://en.wikipedia.org/wiki/Entropy",
        #     "sections": {...}
        # }
    """
    # Try each source in order

    # 1. Local definitions folder
    result = lookup_local(term, vault_path)
    if result:
        # Track this lookup in database
        track_definition_access(term, "local", vault_path)
        return result

    # 2. SQLite cache
    result = lookup_cache(term)
    if result:
        track_definition_access(term, "cache", vault_path)
        return result

    # 3. Stanford Encyclopedia
    result = lookup_stanford(term)
    if result:
        cache_definition(term, result)
        if create_file and vault_path:
            create_definition_file(term, result, vault_path)
        track_definition_access(term, "stanford", vault_path)
        return result

    # 4. Wikipedia (with full sections)
    result = lookup_wikipedia(term)
    if result:
        cache_definition(term, result)
        if create_file and vault_path:
            create_definition_file(term, result, vault_path)
        track_definition_access(term, "wikipedia", vault_path)
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

    # Try different filename formats
    filenames_to_try = [
        term.lower().replace(' ', '_') + '.md',
        term.replace(' ', '_') + '.md',
        term.lower().replace(' ', '-') + '.md',
        term + '.md'
    ]

    for filename in filenames_to_try:
        file_path = os.path.join(vault_path, DEFINITIONS_FOLDER, filename)

        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            return parse_definition_file(term, content, file_path)

    return None


def parse_definition_file(term: str, content: str, file_path: str) -> Dict[str, Any]:
    """
    Parse a definition markdown file with all sections.

    Expected format:
    # Term

    ## Short Definition
    Brief explanation...

    ## Section Name
    Content...
    """
    result = {
        "term": term,
        "short_definition": "",
        "long_definition": "",
        "source": "local",
        "source_url": None,
        "file_path": file_path,
        "sections": {}
    }

    # Extract sections
    sections = re.split(r'^## ', content, flags=re.MULTILINE)

    for section in sections:
        if not section.strip():
            continue

        # Get section name and content
        lines = section.split('\n', 1)
        section_name = lines[0].strip().lower()
        section_content = lines[1].strip() if len(lines) > 1 else ""

        if section_name == 'short definition':
            result["short_definition"] = section_content

        elif section_name == 'long definition':
            result["long_definition"] = section_content

        elif section_name == 'source':
            url_match = re.search(r'https?://[^\s]+', section_content)
            if url_match:
                result["source_url"] = url_match.group()

        else:
            # Store all other sections
            result["sections"][section_name] = section_content

    return result


def lookup_cache(term: str) -> Optional[Dict[str, Any]]:
    """
    Check SQLite cache for a definition.

    Args:
        term: Word to find

    Returns:
        Cached definition if found
    """
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
                "long_definition": result[0].get('long_definition', ''),
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
    """
    if not HAS_REQUESTS:
        return None

    try:
        # Stanford doesn't have a simple API, so we search
        search_term = term.replace(' ', '+')
        url = f"https://plato.stanford.edu/search/searcher.py?query={search_term}"

        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return None

        # Parse search results to find best match
        # This is simplified - real implementation would parse HTML
        if term.lower() in response.text.lower():
            return {
                "term": term,
                "short_definition": f"See Stanford Encyclopedia of Philosophy for detailed information on {term}.",
                "source": "stanford",
                "source_url": f"https://plato.stanford.edu/search/searcher.py?query={search_term}"
            }

    except Exception:
        pass

    return None


def lookup_wikipedia(term: str) -> Optional[Dict[str, Any]]:
    """
    Look up term in Wikipedia with FULL section extraction.

    This fetches:
    - Summary/extract
    - All sections of the article
    - Related links
    - Categories

    Args:
        term: Word to find

    Returns:
        Definition with all sections if found
    """
    if not HAS_REQUESTS:
        return None

    try:
        # Step 1: Get the summary
        summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{term.replace(' ', '_')}"
        response = requests.get(summary_url, timeout=10)

        if response.status_code != 200:
            # Try search if direct lookup fails
            return wikipedia_search(term)

        data = response.json()

        result = {
            "term": data.get("title", term),
            "short_definition": data.get("extract", ""),
            "source": "wikipedia",
            "source_url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
            "sections": {}
        }

        # Step 2: Get full article sections
        sections = get_wikipedia_sections(term)
        if sections:
            result["sections"] = sections
            # Use first section as long definition
            if sections:
                first_section = list(sections.values())[0] if sections else ""
                result["long_definition"] = first_section[:500] + "..." if len(first_section) > 500 else first_section

        # Step 3: Get related links
        related = get_wikipedia_links(term)
        if related:
            result["related_terms"] = related[:10]  # Top 10 related

        return result

    except Exception as e:
        print(f"Wikipedia lookup error: {e}")
        return None


def wikipedia_search(term: str) -> Optional[Dict[str, Any]]:
    """
    Search Wikipedia if direct lookup fails.

    Args:
        term: Search term

    Returns:
        Best match definition
    """
    if not HAS_REQUESTS:
        return None

    try:
        search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={term}&format=json"
        response = requests.get(search_url, timeout=10)

        if response.status_code != 200:
            return None

        data = response.json()
        results = data.get("query", {}).get("search", [])

        if results:
            # Get the first result
            best_match = results[0]["title"]
            # Now look up that article
            return lookup_wikipedia(best_match)

    except Exception:
        pass

    return None


def get_wikipedia_sections(term: str) -> Dict[str, str]:
    """
    Get all sections from a Wikipedia article.

    Args:
        term: Article title

    Returns:
        Dictionary of section_name -> content
    """
    if not HAS_REQUESTS:
        return {}

    try:
        # Get parsed article content
        url = f"https://en.wikipedia.org/w/api.php?action=parse&page={term.replace(' ', '_')}&format=json&prop=sections|text"
        response = requests.get(url, timeout=15)

        if response.status_code != 200:
            return {}

        data = response.json()

        if "error" in data:
            return {}

        sections = {}

        # Get section list
        section_list = data.get("parse", {}).get("sections", [])

        for section in section_list[:10]:  # Limit to first 10 sections
            section_name = section.get("line", "")
            section_index = section.get("index", "")

            if section_name and section_index:
                # Get section content
                section_content = get_wikipedia_section_content(term, section_index)
                if section_content:
                    sections[section_name] = section_content

        return sections

    except Exception:
        return {}


def get_wikipedia_section_content(term: str, section_index: str) -> str:
    """
    Get content of a specific Wikipedia section.

    Args:
        term: Article title
        section_index: Section number

    Returns:
        Section content as plain text
    """
    if not HAS_REQUESTS:
        return ""

    try:
        url = f"https://en.wikipedia.org/w/api.php?action=query&titles={term.replace(' ', '_')}&prop=extracts&exsectionformat=plain&explaintext=true&exsection={section_index}&format=json"
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            return ""

        data = response.json()
        pages = data.get("query", {}).get("pages", {})

        for page_id, page_data in pages.items():
            extract = page_data.get("extract", "")
            # Clean up the extract
            extract = re.sub(r'\n{3,}', '\n\n', extract)  # Remove excessive newlines
            return extract[:2000]  # Limit length

    except Exception:
        pass

    return ""


def get_wikipedia_links(term: str) -> List[str]:
    """
    Get links from a Wikipedia article (related terms).

    Args:
        term: Article title

    Returns:
        List of linked article titles
    """
    if not HAS_REQUESTS:
        return []

    try:
        url = f"https://en.wikipedia.org/w/api.php?action=query&titles={term.replace(' ', '_')}&prop=links&pllimit=50&format=json"
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            return []

        data = response.json()
        pages = data.get("query", {}).get("pages", {})

        links = []
        for page_id, page_data in pages.items():
            for link in page_data.get("links", []):
                title = link.get("title", "")
                # Filter out Wikipedia meta pages
                if not title.startswith(("Wikipedia:", "Help:", "Category:", "Template:", "File:")):
                    links.append(title)

        return links

    except Exception:
        return []


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


def track_definition_access(term: str, source: str, vault_path: str = None) -> bool:
    """
    Track when a definition is accessed.
    This builds the database of every link.

    Args:
        term: The term looked up
        source: Where it was found (local, cache, wikipedia, etc.)
        vault_path: Vault path if applicable

    Returns:
        True if tracked successfully
    """
    try:
        from database.sqlite_db import save_to_sqlite
        from tags.uuid_manager import generate_uuid

        save_to_sqlite({
            "uuid": generate_uuid("lookup"),
            "term": term.lower(),
            "source": source,
            "vault_path": vault_path or "",
            "accessed_at": datetime.now().isoformat()
        }, "definition_access_log")

        return True
    except Exception:
        return False


def create_definition_file(
    term: str,
    definition: Dict[str, Any],
    vault_path: str
) -> str:
    """
    Create a nicely formatted definition file in the vault.
    Includes all sections from Wikipedia.

    Args:
        term: The term being defined
        definition: Definition data (with sections)
        vault_path: Path to Obsidian vault

    Returns:
        Path to created file
    """
    # Ensure definitions folder exists
    def_folder = os.path.join(vault_path, DEFINITIONS_FOLDER)
    if not os.path.exists(def_folder):
        os.makedirs(def_folder)

    # Create filename
    filename = term.lower().replace(' ', '_') + '.md'
    file_path = os.path.join(def_folder, filename)

    # Build content with nice formatting
    lines = [
        f"# {term}",
        "",
        f"> **Source:** {definition.get('source', 'Unknown')}",
        f"> **URL:** {definition.get('source_url', 'N/A')}",
        f"> **Retrieved:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "---",
        "",
        "## Summary",
        "",
        definition.get('short_definition', 'No definition available.'),
        ""
    ]

    # Add long definition if available
    if definition.get('long_definition'):
        lines.extend([
            "## Overview",
            "",
            definition.get('long_definition', ''),
            ""
        ])

    # Add all sections from Wikipedia
    sections = definition.get('sections', {})
    for section_name, section_content in sections.items():
        if section_content:  # Only add non-empty sections
            lines.extend([
                f"## {section_name}",
                "",
                section_content,
                ""
            ])

    # Add related terms if available
    related = definition.get('related_terms', [])
    if related:
        lines.extend([
            "## Related Terms",
            ""
        ])
        for rel_term in related[:15]:  # Limit to 15
            lines.append(f"- [[{rel_term}]]")
        lines.append("")

    # Add metadata footer
    lines.extend([
        "---",
        "",
        "## Metadata",
        "",
        f"- **Term:** {term}",
        f"- **Source:** {definition.get('source', 'Unknown')}",
        f"- **Created:** {datetime.now().isoformat()}",
        f"- **Tags:** #definition #{definition.get('source', 'unknown')}",
        ""
    ])

    # Write file
    content = '\n'.join(lines)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    # Track file creation in database
    try:
        from database.sqlite_db import save_to_sqlite
        from tags.uuid_manager import generate_uuid

        save_to_sqlite({
            "uuid": generate_uuid("def_file"),
            "term": term.lower(),
            "file_path": file_path,
            "source": definition.get("source", "unknown"),
            "created_at": datetime.now().isoformat()
        }, "definition_files")
    except Exception:
        pass

    return file_path


def batch_lookup_definitions(
    terms: List[str],
    vault_path: str = None,
    create_files: bool = True
) -> Dict[str, Any]:
    """
    Look up multiple terms at once.

    Args:
        terms: List of terms to look up
        vault_path: Vault path
        create_files: Whether to create definition files

    Returns:
        Summary of lookups
    """
    results = {
        "found": [],
        "not_found": [],
        "errors": [],
        "files_created": []
    }

    for term in terms:
        try:
            definition = lookup_definition(term, vault_path, create_files)

            if definition:
                results["found"].append({
                    "term": term,
                    "source": definition.get("source"),
                    "short_definition": definition.get("short_definition", "")[:100]
                })

                if create_files and vault_path:
                    file_path = os.path.join(vault_path, DEFINITIONS_FOLDER, f"{term.lower().replace(' ', '_')}.md")
                    if os.path.exists(file_path):
                        results["files_created"].append(file_path)
            else:
                results["not_found"].append(term)

        except Exception as e:
            results["errors"].append({
                "term": term,
                "error": str(e)
            })

    return results
