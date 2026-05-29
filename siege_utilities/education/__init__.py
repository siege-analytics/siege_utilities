"""Education data utilities.

Currently:
- `nces`: NCES CCD + EDGE open data downloader/parsers (CCD Directory,
  Nonfiscal, Finance F-33, school-level Directory + Nonfiscal, EDGE
  per-district demographics).

Future:
- `nces.api`: keyed NCES API (when available).
- `state`: per-state DOE files (highly variable; on-demand basis).
"""

__all__ = ["NCESFiles"]


def __getattr__(name: str):
    if name == "NCESFiles":
        from .nces.files import NCESFiles

        return NCESFiles
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
