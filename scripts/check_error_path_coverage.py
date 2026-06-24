#!/usr/bin/env python3
"""Enforce SU-4b: modules with error paths must have error-path tests.

AST-walks every source file under ``siege_utilities/`` to count except
blocks and raise statements, then cross-references against test files
under ``tests/`` to verify that at least one error-path test exists per
module that contains error sites.

Usage::

    python scripts/check_error_path_coverage.py          # failures only
    python scripts/check_error_path_coverage.py --report  # full table
    python scripts/check_error_path_coverage.py --min-ratio 0.1

Exits 0 when all modules pass, 1 when any module fails.
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------

_ERROR_TEST_KEYWORDS = frozenset(
    {"error", "fail", "invalid", "missing", "raises", "empty", "none"}
)


def _is_import_error_guard(node: ast.ExceptHandler) -> bool:
    """Return True for ``except ImportError: HAS_X = False`` guard patterns."""
    if node.type is None:
        return False
    # Handle both ``except ImportError`` and ``except (ImportError, ...)``.
    names: list[str] = []
    if isinstance(node.type, ast.Name):
        names.append(node.type.id)
    elif isinstance(node.type, ast.Tuple):
        for elt in node.type.elts:
            if isinstance(elt, ast.Name):
                names.append(elt.id)
    if "ImportError" not in names and "ModuleNotFoundError" not in names:
        return False
    # Availability-fallback pattern: the body is made up entirely of simple
    # rebinds — assignments whose right-hand side is a literal constant, a
    # bare name, or an attribute reference. This covers:
    #   except ImportError: HAS_X = False
    #   except ImportError: X = None; X_sql = None
    #   except ImportError: Serializer = drf.ModelSerializer   # fallback class
    # Such a handler only rebinds names to a fallback; it contains no
    # error-handling logic (no calls, no re-raise, no computation), so it is a
    # dependency guard and carries no error-path-test obligation. Restricting
    # the RHS to Constant/Name/Attribute keeps handlers that *compute* a
    # fallback (e.g. ``x = build_stub()``) in scope as real error sites.
    if not node.body:
        return False
    for stmt in node.body:
        if not isinstance(stmt, (ast.Assign, ast.AnnAssign)):
            return False
        value = stmt.value
        if value is None:  # bare annotation, e.g. ``x: int`` — not a rebind
            return False
        if not isinstance(value, (ast.Constant, ast.Name, ast.Attribute)):
            return False
    return True


def _is_finally_cleanup(node: ast.ExceptHandler) -> bool:
    """Heuristic: bare ``except`` that only re-raises is cleanup, not logic."""
    if node.type is not None:
        return False
    if len(node.body) == 1 and isinstance(node.body[0], ast.Raise):
        r = node.body[0]
        if r.exc is None:
            return True
    return False


def count_error_sites(source_path: Path) -> tuple[int, int]:
    """Return (except_count, raise_count) for a source file."""
    try:
        tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    except (SyntaxError, UnicodeDecodeError):
        return 0, 0

    excepts = 0
    raises = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            if _is_import_error_guard(node):
                continue
            if _is_finally_cleanup(node):
                continue
            excepts += 1
        elif isinstance(node, ast.Raise):
            raises += 1
    return excepts, raises


def count_error_path_tests(test_path: Path) -> int:
    """Count error-path tests in a test file."""
    try:
        tree = ast.parse(test_path.read_text(encoding="utf-8"), filename=str(test_path))
    except (SyntaxError, UnicodeDecodeError):
        return 0

    count = 0
    for node in ast.walk(tree):
        # pytest.raises(...) calls
        if isinstance(node, ast.Call):
            func = node.func
            if (
                isinstance(func, ast.Attribute)
                and func.attr == "raises"
                and isinstance(func.value, ast.Name)
                and func.value.id == "pytest"
            ):
                count += 1
        # Test function/method names containing error-path keywords
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("test_"):
                name_lower = node.name.lower()
                if any(kw in name_lower for kw in _ERROR_TEST_KEYWORDS):
                    count += 1
    return count


# ---------------------------------------------------------------------------
# Module-to-test mapping
# ---------------------------------------------------------------------------

def _stem_variants(module_rel: Path) -> list[str]:
    """Generate test file name stems to search for.

    ``siege_utilities/geo/census/catalog.py`` produces candidates like:
    - ``test_catalog``
    - ``test_census_catalog``
    - ``test_geo_census_catalog``
    """
    parts = list(module_rel.with_suffix("").parts)
    # Drop leading ``siege_utilities``
    if parts and parts[0] == "siege_utilities":
        parts = parts[1:]
    # Drop ``__init__`` — use the parent package name instead.
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    if not parts:
        return []
    stems: list[str] = []
    for i in range(len(parts)):
        stems.append("test_" + "_".join(parts[i:]))
    return stems


def _module_import_path(module_rel: Path) -> str:
    """Convert ``siege_utilities/geo/census/catalog.py`` to dotted import path."""
    parts = list(module_rel.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def find_test_files(module_rel: Path, test_dir: Path) -> list[Path]:
    """Find test files that plausibly cover *module_rel*."""
    if not test_dir.is_dir():
        return []
    stems = _stem_variants(module_rel)
    all_tests = list(test_dir.rglob("test_*.py"))
    matched: list[Path] = []

    # Pass 1: name-based matching.
    if stems:
        for tf in all_tests:
            tf_stem = tf.stem
            for candidate in stems:
                if tf_stem == candidate or tf_stem.startswith(candidate + "_"):
                    matched.append(tf)
                    break
                bare = candidate.removeprefix("test_")
                if bare and bare in tf_stem:
                    matched.append(tf)
                    break

    # Pass 2: import-based matching (catches bundled test files like
    # test_config_model_validation.py that cover multiple source modules).
    if not matched:
        import_path = _module_import_path(module_rel)
        if import_path:
            for tf in all_tests:
                try:
                    text = tf.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                if f"from {import_path} import" in text or f"import {import_path}" in text:
                    matched.append(tf)

    return sorted(set(matched))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Check error-path test coverage (SU-4b)."
    )
    ap.add_argument(
        "--report",
        action="store_true",
        help="Show all modules, not just failures.",
    )
    ap.add_argument(
        "--min-ratio",
        type=float,
        default=0.0,
        help="Minimum ratio of error-path tests to error sites (default 0.0).",
    )
    args = ap.parse_args()

    repo = Path(__file__).resolve().parents[1]
    src_root = repo / "siege_utilities"
    test_root = repo / "tests"

    if not src_root.is_dir():
        print(f"ERROR: source root not found: {src_root}", file=sys.stderr)
        return 1

    # Collect all source modules.
    modules: list[Path] = sorted(
        p
        for p in src_root.rglob("*.py")
        if "__pycache__" not in p.parts
    )

    results: list[dict] = []
    for mod_path in modules:
        rel = mod_path.relative_to(repo)
        excepts, raises = count_error_sites(mod_path)
        error_sites = excepts + raises

        test_files = find_test_files(rel, test_root)
        error_tests = sum(count_error_path_tests(tf) for tf in test_files)

        if error_sites == 0:
            verdict = "PASS"
        elif error_tests >= 1:
            if args.min_ratio > 0 and error_sites > 0:
                ratio = error_tests / error_sites
                verdict = "PASS" if ratio >= args.min_ratio else "FAIL"
            else:
                verdict = "PASS"
        else:
            verdict = "FAIL"

        results.append(
            {
                "module": str(rel),
                "excepts": excepts,
                "raises": raises,
                "error_sites": error_sites,
                "has_tests": bool(test_files),
                "error_tests": error_tests,
                "verdict": verdict,
            }
        )

    # Output
    failures = [r for r in results if r["verdict"] == "FAIL"]
    display = results if args.report else failures

    if display:
        # Header
        print(
            f"{'Module':<60s} {'Exc':>4s} {'Raise':>5s} "
            f"{'Sites':>5s} {'Tests?':>6s} {'ErrT':>5s} {'Verdict':>7s}"
        )
        print("-" * 96)
        for r in display:
            print(
                f"{r['module']:<60s} {r['excepts']:>4d} {r['raises']:>5d} "
                f"{r['error_sites']:>5d} {'yes' if r['has_tests'] else 'no':>6s} "
                f"{r['error_tests']:>5d} {r['verdict']:>7s}"
            )

    total = len(results)
    with_sites = sum(1 for r in results if r["error_sites"] > 0)
    passed = sum(1 for r in results if r["verdict"] == "PASS")
    failed = len(failures)

    print()
    print(
        f"Scanned {total} modules: {with_sites} have error sites, "
        f"{passed} pass, {failed} fail."
    )

    if failures:
        print(
            "\nFAIL — modules above have error paths (except/raise) "
            "but no error-path tests.\n"
            "Add tests using pytest.raises() or name test functions with "
            "error/fail/invalid/missing/raises/empty/none keywords."
        )
        return 1

    print("\nOK — all modules with error paths have error-path test coverage.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
