"""
Utilities for working with ReportLab Image objects containing base64 data URIs.

ChartGenerator methods return ReportLab Image objects whose ``filename``
attribute is a base64 data URI (e.g. ``data:image/png;base64,...``).
These helpers decode, display, and persist those images.
"""

import base64
from pathlib import Path
from typing import Optional, Union

from siege_utilities.core.logging import log_info


def decode_rl_image(rl_img) -> Optional[bytes]:
    """Decode a ReportLab Image's base64 data URI to raw PNG bytes.

    Args:
        rl_img: A ReportLab Image object (or any object with a ``filename`` attribute).

    Returns:
        Raw PNG bytes, or ``None`` if the object is not a base64 data URI image.
    """
    if (hasattr(rl_img, 'filename')
            and isinstance(rl_img.filename, str)
            and rl_img.filename.startswith('data:image')):
        b64_data = rl_img.filename.split(',', 1)[1]
        return base64.b64decode(b64_data)
    return None


def show_rl_image(rl_img):
    """Display a ReportLab Image in a Jupyter notebook.

    Decodes the base64 data URI embedded in the ReportLab Image and returns
    an IPython ``Image`` object suitable for inline display.

    Args:
        rl_img: A ReportLab Image object returned by ChartGenerator.

    Returns:
        An ``IPython.display.Image`` for notebook rendering, or the
        original object if it is not a base64 data URI image.
    """
    from IPython.display import Image as IPImage

    png_bytes = decode_rl_image(rl_img)
    if png_bytes is not None:
        return IPImage(data=png_bytes)
    return rl_img


def save_rl_image(rl_img, path: Union[str, Path]) -> Path:
    """Save a ReportLab Image (base64 data URI) to a PNG file.

    Args:
        rl_img: A ReportLab Image object returned by ChartGenerator.
        path: Destination file path.

    Returns:
        The resolved ``Path`` object (unchanged if the image could not be decoded).
    """
    path = Path(path)
    png_bytes = decode_rl_image(rl_img)
    if png_bytes is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(png_bytes)
        log_info(f"Saved: {path}")
    return path
