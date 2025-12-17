"""
AI Classification Engine

This module handles sending notes to AI (like GPT) and getting back
structured classifications (axioms, claims, evidence, etc.)

For beginners:
- This is where we talk to the AI
- We send it a note and a prompt
- It tells us what it found (axioms, claims, etc.)
- We format that into tag blocks
"""

import os
import json
from typing import List, Dict, Any, Optional

# For AI calls - you'll need to install: pip install openai
# from openai import OpenAI


def load_prompt(prompt_type: str) -> str:
    """
    Load a prompt template from the prompts folder.

    Args:
        prompt_type: "axiom", "claim", "evidence", etc.

    Returns:
        The prompt text to send to AI

    Example:
        prompt = load_prompt("axiom")
        # Returns: "Find all statements that are assumed true without proof..."
    """
    # Where we store prompt templates
    prompts_dir = os.path.join(os.path.dirname(__file__), '..', 'prompts')
    prompt_file = os.path.join(prompts_dir, f'{prompt_type}.txt')

    # If we have a saved prompt, use it
    if os.path.exists(prompt_file):
        with open(prompt_file, 'r', encoding='utf-8') as f:
            return f.read()

    # Otherwise use defaults
    default_prompts = {
        'axiom': """
            Analyze the following text and find all AXIOMS.
            An axiom is a statement that is assumed to be true without proof.
            It's a foundational belief that other claims build upon.

            For each axiom found, return it in this format:
            - "The exact quote from the text"

            Return ONLY axioms, nothing else.
        """,
        'claim': """
            Analyze the following text and find all CLAIMS.
            A claim is a statement that asserts something is true
            and could potentially be proven or disproven.

            For each claim found, return it in this format:
            - "The exact quote from the text"

            Return ONLY claims, nothing else.
        """,
        'evidence': """
            Analyze the following text and find all EVIDENCE.
            Evidence is data, observations, or references that
            support or refute claims.

            For each piece of evidence found, return it in this format:
            - "The exact quote from the text"

            Return ONLY evidence, nothing else.
        """,
        'default': """
            Analyze the following text and identify:
            1. Axioms (assumed truths)
            2. Claims (assertions)
            3. Evidence (supporting data)

            Format your response as:
            AXIOMS:
            - "quote"

            CLAIMS:
            - "quote"

            EVIDENCE:
            - "quote"
        """
    }

    return default_prompts.get(prompt_type, default_prompts['default'])


def read_note(note_path: str) -> str:
    """
    Read the content of a markdown note.

    Args:
        note_path: Full path to the .md file

    Returns:
        The text content of the note
    """
    with open(note_path, 'r', encoding='utf-8') as f:
        return f.read()


def call_ai(content: str, prompt: str) -> str:
    """
    Send content and prompt to AI, get response.

    Args:
        content: The note text
        prompt: Instructions for what to find

    Returns:
        AI's response text

    Note for beginners:
        This is where you'd add your OpenAI API key.
        You'll need to sign up at https://platform.openai.com
        and get an API key.
    """
    # TODO: Implement actual AI call
    # For now, return a placeholder

    # Here's what the real code would look like:
    #
    # client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
    #
    # response = client.chat.completions.create(
    #     model="gpt-4",
    #     messages=[
    #         {"role": "system", "content": prompt},
    #         {"role": "user", "content": content}
    #     ]
    # )
    #
    # return response.choices[0].message.content

    # Placeholder for testing
    return """
    AXIOMS:
    - "Space and time are interconnected"

    CLAIMS:
    - "Light bends near massive objects"

    EVIDENCE:
    - "The 1919 eclipse observation confirmed this"
    """


def parse_ai_response(response: str, prompt_type: str) -> List[Dict[str, Any]]:
    """
    Parse AI's text response into structured tag data.

    Args:
        response: Raw text from AI
        prompt_type: What we asked for

    Returns:
        List of tag dictionaries

    Example output:
        [
            {"type": "Axiom", "content": "Space and time are interconnected"},
            {"type": "Claim", "content": "Light bends near massive objects"}
        ]
    """
    tags = []

    # Split into lines and find quoted text
    lines = response.split('\n')

    current_type = prompt_type.capitalize()

    for line in lines:
        line = line.strip()

        # Check for type headers
        if 'AXIOM' in line.upper():
            current_type = 'Axiom'
        elif 'CLAIM' in line.upper():
            current_type = 'Claim'
        elif 'EVIDENCE' in line.upper():
            current_type = 'Evidence'

        # Find quoted content
        if '"' in line:
            # Extract text between quotes
            start = line.find('"') + 1
            end = line.rfind('"')
            if start < end:
                content = line[start:end]
                tags.append({
                    "type": current_type,
                    "content": content
                })

    return tags


def classify_note(note_path: str, prompt_type: str = 'default') -> List[Dict[str, Any]]:
    """
    Main function: Classify a note and return tag blocks.

    This is what gets called from the API.

    Args:
        note_path: Path to the markdown file
        prompt_type: What to look for (axiom, claim, evidence, default)

    Returns:
        List of tags found

    Example:
        tags = classify_note("/vault/notes/physics.md", "axiom")
        # Returns: [{"type": "Axiom", "content": "...", "uuid": "ax-123"}, ...]
    """
    # Import UUID generator
    from tags.uuid_manager import generate_uuid

    # Step 1: Read the note
    content = read_note(note_path)

    # Step 2: Load the prompt
    prompt = load_prompt(prompt_type)

    # Step 3: Call AI
    response = call_ai(content, prompt)

    # Step 4: Parse response into tags
    tags = parse_ai_response(response, prompt_type)

    # Step 5: Add UUIDs to each tag
    for tag in tags:
        tag['uuid'] = generate_uuid(tag['type'].lower())

    return tags


def batch_classify(folder_path: str, prompt_type: str = 'default') -> Dict[str, Any]:
    """
    Classify all notes in a folder.

    Args:
        folder_path: Path to folder containing .md files
        prompt_type: What to look for

    Returns:
        Dictionary with results for each file

    Example:
        results = batch_classify("/vault/Research/", "claim")
        # Returns:
        # {
        #     "processed": 10,
        #     "failed": 0,
        #     "results": {
        #         "paper1.md": [{"type": "Claim", ...}, ...],
        #         "paper2.md": [{"type": "Claim", ...}, ...]
        #     }
        # }
    """
    results = {
        "processed": 0,
        "failed": 0,
        "results": {}
    }

    # Find all .md files
    for filename in os.listdir(folder_path):
        if filename.endswith('.md'):
            note_path = os.path.join(folder_path, filename)

            try:
                tags = classify_note(note_path, prompt_type)
                results["results"][filename] = tags
                results["processed"] += 1
            except Exception as e:
                results["results"][filename] = {"error": str(e)}
                results["failed"] += 1

    return results


def reclassify_with_custom_prompt(note_path: str, custom_prompt: str) -> List[Dict[str, Any]]:
    """
    Classify a note using a custom user-provided prompt.

    Args:
        note_path: Path to the note
        custom_prompt: User's custom instructions

    Returns:
        List of tags found
    """
    from tags.uuid_manager import generate_uuid

    content = read_note(note_path)
    response = call_ai(content, custom_prompt)
    tags = parse_ai_response(response, 'custom')

    for tag in tags:
        tag['uuid'] = generate_uuid(tag['type'].lower())

    return tags
