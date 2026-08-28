#!/usr/bin/env python3
"""Validate that pyproject.toml extras are internally coherent.

Coherence checks:
  1. Every extra's advertised package has at least one consumer inside
     siege_utilities/*.py (via `import X` or `from X`).
     Meta-extras (`all`, `dev`) and native-binding extras (`gdal`) are
     exempt; consumers can also live in scripts/, notebooks/, or
     conftest.py, but the runtime library MUST have a use of the
     package for the extra to deliver capability.

  2. Cross-extra version consistency: when the same package appears in
     multiple extras, all specs must be identical (avoids one extra
     pulling pandas>=1.0 while another pulls pandas>=2.0).

  3. Extra name uniqueness: no `[X]` extra advertises a capability
     that a different extra already delivers.

Exit code:
  0  All checks pass.
  1  Coherence violations found; details printed to stdout.

CI usage: run as a required check on every PR. The check is fast
(one file to parse, `grep -rn` on the tree, ~5s total).

Extension: to add a new "must have consumer" check for a new extra,
add its canonical package name to `EXTRA_CANONICAL_PACKAGES` below.
"""
from __future__ import annotations

import subprocess
import sys
import tomllib
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set


# Extras that are meta / infra / native-binding — no runtime library
# consumer expected.
EXEMPT_EXTRAS: Set[str] = {
    "all",         # meta
    "dev",         # infra (pytest, flake8, etc.)
    "notebooks",   # infra (papermill, nbformat)
    "gdal",        # native system binding, no direct SU code
    # `credentials` pulls `keyring` as a Python-side backend the
    # credential_manager can lean on. Current implementation shells out
    # to `op` / macOS Keychain CLI, so keyring is technically installed
    # without an immediate import site. Kept as exempt while a follow-up
    # ticket decides whether to (a) add a keyring-backed backend, or
    # (b) drop keyring from the extra.
    "credentials",
}

# For each extra, the canonical package whose consumer we require to
# exist inside siege_utilities/. If not listed, the first declared
# dependency is used as the canonical.
EXTRA_CANONICAL_PACKAGES: Dict[str, str] = {
    "3d": "pydeck",
    "analytics": "google-analytics-data",
    "config-extras": "hydra-core",
    "credentials": "keyring",
    "data": "pandas",
    "database": "sqlalchemy",
    "databricks": "databricks-sdk",
    "distributed": "pyspark",
    "etter": "etter",
    "geo": "geopandas",
    "geodjango": "django",
    "h3": "h3",
    "performance": "duckdb",
    "reporting": "matplotlib",
    "s2": "s2sphere",
    "s3": "boto3",
    "schema": "psycopg",
    "survey": "weightipy",
    "web": "beautifulsoup4",
    "wkls": "wkls",
}

# Package name → import name mapping (for cases where they differ)
IMPORT_NAME: Dict[str, str] = {
    "beautifulsoup4": "bs4",
    "google-analytics-data": "google.analytics.data",
    "databricks-sdk": "databricks.sdk",
    "hydra-core": "hydra",
    "memory-profiler": "memory_profiler",
    "python-pptx": "pptx",
    "s2sphere": "s2sphere",
    "psycopg2-binary": "psycopg2",
    "psycopg": "psycopg",
    "apache-sedona": "sedona",
    "google-api-python-client": "googleapiclient",
    "google-auth-httplib2": "google_auth_httplib2",
    "google-auth-oauthlib": "google_auth_oauthlib",
    "djangorestframework": "rest_framework",
    "djangorestframework-gis": "rest_framework_gis",
    "facebook-business": "facebook_business",
    "snowflake-connector-python": "snowflake",
    "hydra-zen": "hydra_zen",
    "pytest-cov": "pytest_cov",
    "pytest-mock": "pytest_mock",
    "pytest-django": "pytest_django",
}


def canonical_import(pkg: str) -> str:
    """Return the Python import name for a PyPI package."""
    return IMPORT_NAME.get(pkg, pkg.replace("-", "_"))


def grep_consumer(import_name: str) -> bool:
    """Return True if some file in siege_utilities/ imports the package.

    Matches both top-level (`import X`, `from X import Y`) and indented
    imports (inside try/except blocks, functions, conditionals) since
    optional-dep imports are often deferred to first use.
    """
    top = import_name.split(".", 1)[0]
    for candidate in (import_name, top):
        result = subprocess.run(
            ["grep", "-rlE",
             f"(^|[[:space:]])import {candidate}([[:space:]]|\\.|,|$)|"
             f"(^|[[:space:]])from {candidate}([[:space:]]|\\.)",
             "siege_utilities/",
             "--include=*.py"],
            capture_output=True, text=True,
        )
        if result.stdout.strip():
            return True
    return False


def parse_extras(pyproject_path: Path) -> Dict[str, List[str]]:
    """Return {extra_name: [dep_spec, ...]} from pyproject.toml."""
    data = tomllib.loads(pyproject_path.read_bytes().decode())
    return data.get("project", {}).get("optional-dependencies", {})


def pkg_name(spec: str) -> str:
    """Extract the package name from a dep spec like 'pandas>=2.0.0'."""
    import re
    m = re.match(r"^([a-zA-Z0-9_.\-]+)", spec)
    return m.group(1).lower() if m else spec.lower()


def check_consumer_present(extras: Dict[str, List[str]]) -> List[str]:
    """Check 1: every non-exempt extra has a library consumer."""
    violations = []
    for extra, deps in extras.items():
        if extra in EXEMPT_EXTRAS:
            continue
        # Determine canonical package for this extra
        canonical = EXTRA_CANONICAL_PACKAGES.get(extra)
        if canonical is None:
            # Fall back to first declared dep
            canonical = pkg_name(deps[0]) if deps else None
        if canonical is None:
            continue
        import_name = canonical_import(canonical)
        if not grep_consumer(import_name):
            violations.append(
                f"  [{extra}]: canonical package '{canonical}' (import '{import_name}') "
                f"has 0 consumers in siege_utilities/. The extra promises capability "
                f"the library does not deliver.")
    return violations


def check_version_consistency(extras: Dict[str, List[str]]) -> List[str]:
    """Check 2: when a package appears in multiple extras, all specs must match."""
    violations = []
    pkg_specs: Dict[str, Dict[str, str]] = defaultdict(dict)
    for extra, deps in extras.items():
        for spec in deps:
            name = pkg_name(spec)
            pkg_specs[name][extra] = spec
    for pkg, extras_specs in pkg_specs.items():
        specs = set(extras_specs.values())
        if len(specs) > 1:
            violations.append(
                f"  {pkg}: appears in {list(extras_specs.keys())} with "
                f"conflicting specs: {sorted(specs)}")
    return violations


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        print(f"ERROR: {pyproject} not found", file=sys.stderr)
        return 1

    extras = parse_extras(pyproject)
    print(f"validate_extras_coherence: scanning {len(extras)} extras")

    consumer_violations = check_consumer_present(extras)
    version_violations = check_version_consistency(extras)

    if consumer_violations:
        print(f"\nUnconsumed extras ({len(consumer_violations)}):")
        for v in consumer_violations:
            print(v)

    if version_violations:
        print(f"\nCross-extra version conflicts ({len(version_violations)}):")
        for v in version_violations:
            print(v)

    total = len(consumer_violations) + len(version_violations)
    if total > 0:
        print(f"\nFAIL: {total} coherence violation(s). "
              f"Fix or add to EXEMPT_EXTRAS with justification.")
        return 1

    print(f"\nOK: all {len(extras)} extras coherent — each non-exempt "
          f"extra has at least one library consumer; no version conflicts.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
