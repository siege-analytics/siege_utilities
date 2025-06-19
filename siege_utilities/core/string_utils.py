import logging

from django.db.models.fields import return_None

logger = logging.getLogger(__name__)


def remove_wrapping_quotes_and_trim(target_string: str) ->str:
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
