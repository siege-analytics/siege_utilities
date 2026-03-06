#!/usr/bin/env python3
"""Validate tracked test file naming/location conventions."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT_TEST_RE = re.compile(r"^test_[A-Za-z0-9_]+\.py$")
TESTS_FILE_RE = re.compile(r"^tests/(?:[A-Za-z0-9_]+/)*test_[a-z0-9_]+\.py$")
ADHOC_COPY_RE = re.compile(r"(^|/)test_.*\s+\d+\.py$")


def tracked_files() -> list[str]:
    try:
        out = subprocess.check_output(["git", "ls-files"], text=True)
        return [line.strip() for line in out.splitlines() if line.strip()]
    except Exception:
        # Fallback for environments without git metadata.
        return [str(p.as_posix()) for p in Path(".").rglob("*") if p.is_file()]


def main() -> int:
    violations: list[str] = []

    for path in tracked_files():
        name = Path(path).name

        if ADHOC_COPY_RE.search(path):
            violations.append(
                f"{path}: duplicate/ad hoc copy pattern detected (e.g., trailing numeric copy)"
            )

        if "/" not in path and ROOT_TEST_RE.match(name):
            violations.append(
                f"{path}: test files must live under tests/ as tests/test_<feature>.py"
            )

        if path.startswith("tests/") and name.startswith("test_") and not TESTS_FILE_RE.match(path):
            violations.append(
                f"{path}: invalid test filename, expected tests/test_<lower_snake_case>.py"
            )

    if violations:
        print("Test file hygiene check: FAIL")
        for issue in sorted(set(violations)):
            print(f"- {issue}")
        return 1

    print("Test file hygiene check: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
