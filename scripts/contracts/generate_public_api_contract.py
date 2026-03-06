#!/usr/bin/env python3
"""
Generate a deterministic public API contract manifest for a Python package.
"""

from __future__ import annotations

import argparse
import inspect
import json
from datetime import datetime, timezone
from importlib import import_module
from typing import Any, Dict


def _safe_signature(obj: Any) -> str | None:
    """Return a stable string signature when available."""
    try:
        return str(inspect.signature(obj))
    except (TypeError, ValueError):
        return None


def _symbol_kind(obj: Any) -> str:
    if inspect.isclass(obj):
        return "class"
    if inspect.isfunction(obj):
        return "function"
    if inspect.ismethod(obj):
        return "method"
    if inspect.isbuiltin(obj):
        return "builtin"
    if callable(obj):
        return "callable"
    return type(obj).__name__


def build_contract(package_name: str) -> Dict[str, Any]:
    """Build an in-memory contract from the package's public symbols."""
    pkg = import_module(package_name)
    package_version = getattr(pkg, "__version__", "unknown")

    symbols: Dict[str, Dict[str, Any]] = {}
    for name in sorted(n for n in dir(pkg) if not n.startswith("_")):
        try:
            obj = getattr(pkg, name)
        except Exception as exc:  # pragma: no cover - defensive
            symbols[name] = {
                "kind": "unresolved",
                "signature": None,
                "module": None,
                "qualname": None,
                "error": f"{type(exc).__name__}: {exc}",
            }
            continue

        symbols[name] = {
            "kind": _symbol_kind(obj),
            "signature": _safe_signature(obj) if callable(obj) else None,
            "module": getattr(obj, "__module__", None),
            "qualname": getattr(obj, "__qualname__", None),
        }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "package": package_name,
        "package_version": package_version,
        "symbol_count": len(symbols),
        "callable_count": sum(1 for v in symbols.values() if v.get("signature") is not None),
        "symbols": symbols,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate public API contract manifest.")
    parser.add_argument("--package", default="siege_utilities", help="Package import name.")
    parser.add_argument("--output", required=True, help="Output JSON file path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    contract = build_contract(args.package)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(contract, f, indent=2, sort_keys=True)
    print(
        f"Wrote contract for {contract['package']}@{contract['package_version']} "
        f"with {contract['symbol_count']} symbols -> {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
