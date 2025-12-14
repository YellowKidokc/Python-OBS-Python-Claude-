"""
Prompt Manager

Handles saving, loading, and managing custom prompts
for the classification system.

For beginners:
- Users can customize the AI prompts
- This module saves and loads those customizations
- Prompts are stored as simple text files
"""

import os
from typing import Dict, Optional

# Where prompts are stored
PROMPTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'prompts')


def ensure_prompts_dir():
    """Make sure the prompts directory exists."""
    if not os.path.exists(PROMPTS_DIR):
        os.makedirs(PROMPTS_DIR)


def save_prompt(prompt_type: str, prompt_text: str) -> bool:
    """
    Save a custom prompt.

    Args:
        prompt_type: "axiom", "claim", etc.
        prompt_text: The actual prompt instructions

    Returns:
        True if saved successfully
    """
    ensure_prompts_dir()

    file_path = os.path.join(PROMPTS_DIR, f'{prompt_type}.txt')

    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(prompt_text)
        return True
    except Exception:
        return False


def load_prompt(prompt_type: str) -> Optional[str]:
    """
    Load a saved prompt.

    Args:
        prompt_type: "axiom", "claim", etc.

    Returns:
        The prompt text, or None if not found
    """
    file_path = os.path.join(PROMPTS_DIR, f'{prompt_type}.txt')

    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()

    return None


def list_prompts() -> Dict[str, str]:
    """
    List all saved prompts.

    Returns:
        Dictionary of prompt_type -> prompt_text
    """
    ensure_prompts_dir()
    prompts = {}

    for filename in os.listdir(PROMPTS_DIR):
        if filename.endswith('.txt'):
            prompt_type = filename[:-4]  # Remove .txt
            prompts[prompt_type] = load_prompt(prompt_type)

    return prompts


def delete_prompt(prompt_type: str) -> bool:
    """
    Delete a custom prompt (reverts to default).

    Args:
        prompt_type: "axiom", "claim", etc.

    Returns:
        True if deleted successfully
    """
    file_path = os.path.join(PROMPTS_DIR, f'{prompt_type}.txt')

    if os.path.exists(file_path):
        os.remove(file_path)
        return True

    return False


def get_default_prompts() -> Dict[str, str]:
    """
    Get the built-in default prompts.

    Returns:
        Dictionary of all default prompts
    """
    return {
        'axiom': """
Analyze the following text and find all AXIOMS.

An axiom is a statement that:
- Is assumed to be true without requiring proof
- Serves as a foundational belief or starting point
- Other claims or arguments build upon it

For each axiom found, extract the exact quote from the text.

Format your response as a list:
- "First axiom quote here"
- "Second axiom quote here"
        """.strip(),

        'claim': """
Analyze the following text and find all CLAIMS.

A claim is a statement that:
- Asserts something is true or false
- Could potentially be proven or disproven
- Makes a testable assertion

For each claim found, extract the exact quote from the text.

Format your response as a list:
- "First claim quote here"
- "Second claim quote here"
        """.strip(),

        'evidence': """
Analyze the following text and find all EVIDENCE.

Evidence is:
- Data, observations, or experimental results
- References to studies or research
- Supporting material for claims

For each piece of evidence, extract the exact quote from the text.

Format your response as a list:
- "First evidence quote here"
- "Second evidence quote here"
        """.strip(),

        'theory': """
Analyze the following text and identify the main THEORY being discussed.

A theory is:
- A well-substantiated explanation of phenomena
- Supported by evidence and testing
- Makes predictions about the world

Describe the theory and extract key statements about it.

Format your response as:
THEORY NAME: [Name]
KEY STATEMENTS:
- "Quote 1"
- "Quote 2"
        """.strip(),

        'definition': """
Find all DEFINITIONS in the following text.

A definition:
- Explains what a term or concept means
- May use phrases like "is defined as", "refers to", "means"
- Provides clarity on terminology

For each definition found, extract:
TERM: [The word being defined]
DEFINITION: "The explanation given"
        """.strip()
    }
