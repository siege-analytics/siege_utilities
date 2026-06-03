"""Vector dataset file discovery utilities."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Sequence

log = logging.getLogger(__name__)

__all__ = [
    "VALID_VECTOR_EXTENSIONS",
    "find_vector_dataset_file_in_directory",
]

VALID_VECTOR_EXTENSIONS = (".shp", ".geojson", ".gpkg", ".gml", ".kml", ".fgb")


def find_vector_dataset_file_in_directory(
    directory,
    extensions: Optional[Sequence[str]] = None,
) -> Optional[Path]:
    """Find a vector dataset file in a directory.

    Searches *directory* recursively for files matching common
    geospatial vector formats.  Returns the first match found.

    Args:
        directory: Directory path to search (str or Path).
        extensions: Sequence of file extensions to match, including
            the leading dot (e.g. ``[".shp", ".geojson"]``).  Defaults
            to :data:`VALID_VECTOR_EXTENSIONS`.

    Returns:
        :class:`~pathlib.Path` to the first matching file, or ``None``
        if no vector file is found.
    """
    if extensions is None:
        extensions = VALID_VECTOR_EXTENSIONS
    directory = Path(directory)
    if not directory.is_dir():
        log.warning("Directory does not exist: %s", directory)
        return None
    for ext in extensions:
        matches = sorted(directory.rglob(f"*{ext}"))
        if matches:
            return matches[0]
    return None
