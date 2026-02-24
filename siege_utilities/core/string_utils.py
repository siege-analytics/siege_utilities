import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


def remove_wrapping_quotes_and_trim(target_string: str) -> str:
    """
    Removes wrapping quotes (single or double) from a string and trims whitespace

    Args:
        target_string: String that may have wrapping quotes and whitespace

    Returns:
        String with any wrapping quotes and whitespace removed
    """
    if target_string is None:
        return ''
    strings_to_ignore = ['', '\n']
    if target_string in strings_to_ignore:
        return_string = target_string
        return return_string
    return_string = target_string.strip()
    wrapping_characters = ['"', "'"]
    if len(return_string) >= 2:
        first_char = return_string[0]
        last_char = return_string[-1]
        if first_char == last_char and first_char in wrapping_characters:
            return_string = return_string[1:-1].strip()
    return return_string


def clean_string(target_string: Optional[str]) -> str:
    """
    Clean a string by removing quotes, trimming whitespace, and normalizing.

    Args:
        target_string: String to clean

    Returns:
        Cleaned string
    """
    if not target_string:
        return ""

    cleaned = remove_wrapping_quotes_and_trim(target_string)
    cleaned = normalize_whitespace(cleaned)
    return cleaned


def normalize_whitespace(target_string: Optional[str]) -> str:
    """
    Normalize whitespace in a string by replacing multiple spaces with single space.

    Args:
        target_string: String to normalize

    Returns:
        String with normalized whitespace

    Examples:
        >>> normalize_whitespace("hello    world")
        'hello world'
        >>> normalize_whitespace("test\\n\\n\\nvalue")
        'test value'
    """
    if not target_string:
        return ""

    normalized = re.sub(r"\s+", " ", target_string)
    return normalized.strip()


def snake_case(text: str) -> str:
    """
    Convert text to snake_case.

    Args:
        text: Text to convert

    Returns:
        snake_case version of text

    Examples:
        >>> snake_case("HelloWorld")
        'hello_world'
        >>> snake_case("hello-world")
        'hello_world'
        >>> snake_case("Hello World")
        'hello_world'
    """
    if not text:
        return ""

    text = text.replace("-", "_").replace(" ", "_")
    text = re.sub("([a-z0-9])([A-Z])", r"\1_\2", text)
    return text.lower()


def remove_non_alphanumeric(text: str, keep_chars: str = "_-") -> str:
    """
    Remove non-alphanumeric characters from text, optionally keeping specified chars.

    Args:
        text: Text to clean
        keep_chars: Characters to keep (default: underscore and hyphen)

    Returns:
        Cleaned text

    Examples:
        >>> remove_non_alphanumeric("hello@world!")
        'helloworld'
        >>> remove_non_alphanumeric("test_value-123", keep_chars="_-")
        'test_value-123'
    """
    if not text:
        return ""

    pattern = f"[^a-zA-Z0-9{re.escape(keep_chars)}]"
    return re.sub(pattern, "", text)
