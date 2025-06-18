# python stdlib imports
import logging

logger = logging.getLogger(__name__)


def remove_wrapping_quotes_and_trim(target_string: str) -> str:
    """
    Removes wrapping quotes (single or double) from a string and trims whitespace

    Args:
        target_string: String that may have wrapping quotes and whitespace

    Returns:
        String with any wrapping quotes and whitespace removed
    """
    # Check for None or empty strings first
    if target_string is None:
        return ""

    # Handle empty strings and newlines
    strings_to_ignore = ["", "\n"]
    if target_string in strings_to_ignore:
        return target_string.strip()

    # Start by trimming whitespace
    return_string = target_string.strip()

    # Check for wrapping quotes
    wrapping_characters = ['"', "'"]

    # Only proceed if string has at least 2 characters (needed for first/last char check)
    if len(return_string) >= 2:
        first_char = return_string[0]
        last_char = return_string[-1]

        # Check if string is wrapped in quotes
        if first_char == last_char and first_char in wrapping_characters:
            # Remove the wrapping quotes and trim any resulting whitespace
            return_string = return_string[1:-1].strip()

    return return_string
