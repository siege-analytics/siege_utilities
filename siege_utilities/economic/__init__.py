"""Economic data utilities.

Currently:
- `bls.qcew`: BLS Quarterly Census of Employment and Wages downloader/parser.
- `irs.soi`: IRS Statistics of Income by ZIP code.

Future:
- `bls.api`: keyed-API client for incremental loads.
- `bea`: BEA Regional Economic Accounts.
"""

__all__ = ["IRSSOIFiles", "QCEWFiles"]

_LAZY = {
    "QCEWFiles": ".bls.qcew",
    "IRSSOIFiles": ".irs.soi",
}


def __getattr__(name: str):
    if name in _LAZY:
        import importlib
        mod = importlib.import_module(_LAZY[name], __package__)
        return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
