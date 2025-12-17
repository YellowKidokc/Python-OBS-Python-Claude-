"""
Term Finder

Scans notes to find proper nouns, keywords, and phrases
that should be linked to definitions.

For beginners:
- This finds important words in your notes
- Things like "Einstein", "Quantum Mechanics", "entropy"
- These get linked to their definitions automatically
"""

import re
from typing import List, Dict, Any, Set


# Common words to ignore (not proper nouns or keywords)
STOP_WORDS = {
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
    'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
    'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that',
    'these', 'those', 'it', 'its', 'they', 'them', 'their', 'we', 'us',
    'our', 'you', 'your', 'he', 'him', 'his', 'she', 'her', 'i', 'my',
    'me', 'who', 'which', 'what', 'when', 'where', 'why', 'how', 'all',
    'each', 'every', 'both', 'few', 'more', 'most', 'other', 'some',
    'such', 'no', 'not', 'only', 'same', 'so', 'than', 'too', 'very',
    'just', 'also', 'now', 'here', 'there', 'then', 'about', 'after',
    'before', 'between', 'into', 'through', 'during', 'under', 'over',
    'again', 'further', 'once', 'any', 'if', 'because', 'until', 'while'
}

# Domain-specific keywords to always capture
DOMAIN_KEYWORDS = {
    # Physics
    'entropy', 'gravity', 'relativity', 'quantum', 'spacetime',
    'electromagnetism', 'thermodynamics', 'mechanics', 'particle',
    # Philosophy
    'axiom', 'theorem', 'hypothesis', 'epistemology', 'ontology',
    'metaphysics', 'ethics', 'logic', 'dialectic', 'phenomenology',
    # Math
    'calculus', 'algebra', 'geometry', 'topology', 'infinity',
    'derivative', 'integral', 'matrix', 'vector', 'tensor',
    # General academic
    'theory', 'principle', 'law', 'model', 'paradigm', 'framework'
}


def find_terms(note_path: str) -> List[Dict[str, Any]]:
    """
    Find all important terms in a note.

    Args:
        note_path: Path to the markdown file

    Returns:
        List of found terms with metadata

    Example:
        terms = find_terms("/vault/notes/physics.md")
        # Returns:
        # [
        #     {"term": "Einstein", "type": "proper_noun", "count": 3},
        #     {"term": "relativity", "type": "keyword", "count": 5}
        # ]
    """
    with open(note_path, 'r', encoding='utf-8') as f:
        content = f.read()

    return find_terms_in_content(content)


def find_terms_in_content(content: str) -> List[Dict[str, Any]]:
    """
    Extract terms from content string.

    Args:
        content: The note text

    Returns:
        List of term dictionaries
    """
    terms = {}

    # Remove markdown formatting for cleaner analysis
    clean_content = clean_markdown(content)

    # Find proper nouns (capitalized words not at sentence start)
    proper_nouns = find_proper_nouns(clean_content)
    for term in proper_nouns:
        if term not in terms:
            terms[term] = {"term": term, "type": "proper_noun", "count": 0}
        terms[term]["count"] += 1

    # Find capitalized phrases (like "Quantum Mechanics")
    phrases = find_capitalized_phrases(clean_content)
    for phrase in phrases:
        if phrase not in terms:
            terms[phrase] = {"term": phrase, "type": "phrase", "count": 0}
        terms[phrase]["count"] += 1

    # Find domain keywords
    keywords = find_domain_keywords(clean_content)
    for keyword in keywords:
        if keyword not in terms:
            terms[keyword] = {"term": keyword, "type": "keyword", "count": 0}
        terms[keyword]["count"] += 1

    return list(terms.values())


def clean_markdown(content: str) -> str:
    """
    Remove markdown formatting to get clean text.

    Args:
        content: Raw markdown

    Returns:
        Clean text
    """
    # Remove code blocks
    content = re.sub(r'```[\s\S]*?```', '', content)
    content = re.sub(r'`[^`]+`', '', content)

    # Remove links but keep text
    content = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', content)

    # Remove headers markers
    content = re.sub(r'^#+\s*', '', content, flags=re.MULTILINE)

    # Remove bold/italic markers
    content = re.sub(r'\*\*([^*]+)\*\*', r'\1', content)
    content = re.sub(r'\*([^*]+)\*', r'\1', content)
    content = re.sub(r'__([^_]+)__', r'\1', content)
    content = re.sub(r'_([^_]+)_', r'\1', content)

    # Remove tag blocks
    content = re.sub(r'%%[^%]+%%', '', content)

    return content


def find_proper_nouns(content: str) -> List[str]:
    """
    Find capitalized words that aren't at sentence starts.

    Args:
        content: Clean text

    Returns:
        List of proper nouns
    """
    proper_nouns = []

    # Split into sentences
    sentences = re.split(r'[.!?]\s+', content)

    for sentence in sentences:
        words = sentence.split()

        # Skip first word of sentence (capitalized by default)
        for word in words[1:]:
            # Remove punctuation
            clean_word = re.sub(r'[^\w]', '', word)

            # Check if capitalized and not a stop word
            if clean_word and clean_word[0].isupper():
                if clean_word.lower() not in STOP_WORDS:
                    proper_nouns.append(clean_word)

    return proper_nouns


def find_capitalized_phrases(content: str) -> List[str]:
    """
    Find multi-word capitalized phrases like "General Relativity".

    Args:
        content: Clean text

    Returns:
        List of phrases
    """
    phrases = []

    # Pattern for 2-4 word capitalized phrases
    pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b'

    matches = re.findall(pattern, content)

    for match in matches:
        # Filter out common phrases
        if not any(word.lower() in STOP_WORDS for word in match.split()):
            phrases.append(match)

    return phrases


def find_domain_keywords(content: str) -> List[str]:
    """
    Find known domain-specific keywords.

    Args:
        content: Clean text

    Returns:
        List of keywords found
    """
    found = []
    content_lower = content.lower()

    for keyword in DOMAIN_KEYWORDS:
        if keyword in content_lower:
            found.append(keyword)

    return found


def add_custom_term(term: str) -> bool:
    """
    Add a term to the keywords list.

    This lets users add terms the system missed.

    Args:
        term: Word to add

    Returns:
        True if added
    """
    DOMAIN_KEYWORDS.add(term.lower())
    return True


def get_term_locations(content: str, term: str) -> List[Dict[str, int]]:
    """
    Find where a term appears in content.

    Args:
        content: The text
        term: Word to find

    Returns:
        List of locations (line, column)
    """
    locations = []
    lines = content.split('\n')

    for line_num, line in enumerate(lines, 1):
        # Case-insensitive search
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        for match in pattern.finditer(line):
            locations.append({
                "line": line_num,
                "column": match.start() + 1,
                "context": line.strip()
            })

    return locations
