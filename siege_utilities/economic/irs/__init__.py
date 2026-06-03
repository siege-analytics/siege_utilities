"""IRS economic data utilities.

Currently:
- `soi`: IRS Statistics of Income by ZIP code.
"""

__all__ = ["IRSSOIFiles"]


def __getattr__(name: str):
    if name == "IRSSOIFiles":
        from .soi import IRSSOIFiles

        return IRSSOIFiles
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
