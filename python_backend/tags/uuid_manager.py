"""
UUID Manager

Handles creating unique identifiers for everything in the system.

For beginners:
- UUID = "Universally Unique Identifier"
- It's like a social security number for your data
- No two things ever get the same UUID
- We use prefixes to know what type of thing it is

Example UUIDs:
- note_abc123def456
- claim_xyz789ghi012
- sent_mno345pqr678
"""

import uuid
from datetime import datetime
from typing import Optional


def generate_uuid(entity_type: str = 'generic') -> str:
    """
    Generate a new unique identifier with a type prefix.

    Args:
        entity_type: What kind of thing is this?
            - "note" for notes
            - "para" for paragraphs
            - "sent" for sentences
            - "term" for terms/words
            - "axiom" for axiom tags
            - "claim" for claim tags
            - "evidence" for evidence tags
            - "def" for definitions
            - "link" for links

    Returns:
        A string like "claim-7x3f9k2m"

    Example:
        uuid1 = generate_uuid("claim")   # "claim-a1b2c3d4"
        uuid2 = generate_uuid("note")    # "note-e5f6g7h8"
    """
    # Generate a random UUID (this is guaranteed unique)
    raw_uuid = uuid.uuid4()

    # Take just the first 8 characters (still very unique)
    short_id = str(raw_uuid).replace('-', '')[:8]

    # Combine with prefix
    # Normalize the entity type (lowercase, no spaces)
    prefix = entity_type.lower().replace(' ', '_')

    return f"{prefix}-{short_id}"


def generate_deterministic_uuid(content: str, entity_type: str = 'generic') -> str:
    """
    Generate a UUID based on content (same content = same UUID).

    This is useful when you want the same text to always get
    the same identifier.

    Args:
        content: The text content
        entity_type: What kind of thing

    Returns:
        A reproducible UUID

    Example:
        # These will always be the same:
        uuid1 = generate_deterministic_uuid("gravity", "term")
        uuid2 = generate_deterministic_uuid("gravity", "term")
        assert uuid1 == uuid2  # True!
    """
    # Use uuid5 with a namespace - same input = same output
    namespace = uuid.NAMESPACE_DNS
    raw_uuid = uuid.uuid5(namespace, f"{entity_type}:{content}")

    short_id = str(raw_uuid).replace('-', '')[:8]
    prefix = entity_type.lower().replace(' ', '_')

    return f"{prefix}-{short_id}"


def extract_entity_type(uuid_string: str) -> Optional[str]:
    """
    Get the entity type from a UUID.

    Args:
        uuid_string: A UUID like "claim-abc12345"

    Returns:
        The type, like "claim"

    Example:
        entity_type = extract_entity_type("claim-abc12345")
        # Returns: "claim"
    """
    if '-' in uuid_string:
        return uuid_string.split('-')[0]
    return None


def is_valid_uuid(uuid_string: str) -> bool:
    """
    Check if a string looks like a valid UUID from our system.

    Args:
        uuid_string: String to check

    Returns:
        True if it looks valid

    Example:
        is_valid_uuid("claim-abc12345")  # True
        is_valid_uuid("random text")     # False
    """
    if not uuid_string or '-' not in uuid_string:
        return False

    parts = uuid_string.split('-')
    if len(parts) != 2:
        return False

    # Prefix should be alphabetic
    if not parts[0].replace('_', '').isalpha():
        return False

    # ID should be alphanumeric and 8 characters
    if len(parts[1]) != 8 or not parts[1].isalnum():
        return False

    return True


def generate_timestamp_uuid(entity_type: str = 'generic') -> str:
    """
    Generate a UUID that includes a timestamp component.

    Useful for when you need to sort things by creation time.

    Args:
        entity_type: What kind of thing

    Returns:
        UUID with timestamp component
    """
    # Get current timestamp as hex
    timestamp = hex(int(datetime.now().timestamp()))[2:]  # Remove '0x'

    # Add random component
    random_part = str(uuid.uuid4()).replace('-', '')[:4]

    prefix = entity_type.lower().replace(' ', '_')

    return f"{prefix}-{timestamp[-4:]}{random_part}"


# ============================================
# UUID REGISTRY (Optional - for tracking)
# ============================================

class UUIDRegistry:
    """
    Optional: Keep track of all UUIDs we've created.

    This is useful for:
    - Preventing duplicates
    - Looking up what a UUID refers to
    - Debugging
    """

    def __init__(self):
        self._registry = {}

    def register(self, uuid_str: str, metadata: dict = None) -> bool:
        """
        Register a new UUID.

        Args:
            uuid_str: The UUID
            metadata: Optional info about what it represents

        Returns:
            True if registered (False if already exists)
        """
        if uuid_str in self._registry:
            return False

        self._registry[uuid_str] = {
            'created_at': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        return True

    def lookup(self, uuid_str: str) -> Optional[dict]:
        """
        Look up information about a UUID.

        Args:
            uuid_str: The UUID to look up

        Returns:
            Metadata if found, None otherwise
        """
        return self._registry.get(uuid_str)

    def exists(self, uuid_str: str) -> bool:
        """Check if a UUID is registered."""
        return uuid_str in self._registry

    def get_all(self, entity_type: str = None) -> list:
        """
        Get all registered UUIDs.

        Args:
            entity_type: Optional filter by type

        Returns:
            List of UUIDs
        """
        if entity_type:
            prefix = entity_type.lower() + '-'
            return [u for u in self._registry.keys() if u.startswith(prefix)]
        return list(self._registry.keys())


# Global registry instance
_registry = UUIDRegistry()


def register_uuid(uuid_str: str, metadata: dict = None) -> bool:
    """Register a UUID in the global registry."""
    return _registry.register(uuid_str, metadata)


def lookup_uuid(uuid_str: str) -> Optional[dict]:
    """Look up a UUID in the global registry."""
    return _registry.lookup(uuid_str)
