import importlib.util
import sys
from pathlib import Path


def _load_module(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    # Dataclass metadata resolution expects the module to be registered.
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _contract(symbols):
    return {
        "package": "siege_utilities",
        "package_version": "x.y.z",
        "symbols": symbols,
    }


def test_patch_disallows_additions_and_signature_changes():
    mod = _load_module(
        "compare_contracts",
        Path("scripts/contracts/compare_public_api_contracts.py"),
    )

    baseline = _contract(
        {
            "foo": {"kind": "function", "signature": "(x)"},
            "bar": {"kind": "function", "signature": "()"},
        }
    )
    candidate = _contract(
        {
            "foo": {"kind": "function", "signature": "(x, y=None)"},
            "bar": {"kind": "function", "signature": "()"},
            "baz": {"kind": "function", "signature": "()"},
        }
    )

    diff = mod.diff_contracts(baseline, candidate)
    ok, errors = mod.evaluate(diff, "patch")

    assert not ok
    assert any("cannot add symbols" in e for e in errors)
    assert any("cannot change signatures" in e for e in errors)


def test_minor_allows_additions_but_not_removals():
    mod = _load_module(
        "compare_contracts_minor",
        Path("scripts/contracts/compare_public_api_contracts.py"),
    )

    baseline = _contract({"foo": {"kind": "function", "signature": "()"}})
    candidate = _contract({"foo2": {"kind": "function", "signature": "()"}})

    diff = mod.diff_contracts(baseline, candidate)
    ok, errors = mod.evaluate(diff, "minor")

    assert not ok
    assert any("cannot remove symbols" in e for e in errors)


def test_allowlist_filters_changes_before_evaluation():
    mod = _load_module(
        "compare_contracts_allow",
        Path("scripts/contracts/compare_public_api_contracts.py"),
    )

    baseline = _contract({"foo": {"kind": "function", "signature": "(x)"}})
    candidate = _contract({"foo": {"kind": "function", "signature": "(x, y=None)"}})

    raw = mod.diff_contracts(baseline, candidate)
    filtered = mod.apply_allowlist(raw, {"signature_changes": ["foo"]})
    ok, _ = mod.evaluate(filtered, "major")

    assert ok
