"""Fail when the test suite leaves new files or directories in the checkout (#1693).

``git status`` does not show empty directories, and most test litter is
exactly that (``reports/``, ``presentations/``...), so this compares
``git ls-files --others --exclude-standard --directory`` before and after.
Ignored caches (.hypothesis, coverage files) are excluded by .gitignore.

Usage:
    python scripts/check_test_litter.py snapshot <state-file>
    pytest ...
    python scripts/check_test_litter.py compare <state-file>
"""

import subprocess
import sys
from pathlib import Path


def untracked_paths() -> set[str]:
    out = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "--directory", "-z"],
        capture_output=True, text=True, check=True, timeout=120,
    ).stdout
    return {p for p in out.split("\0") if p}


def main(argv: list[str]) -> int:
    if len(argv) != 3 or argv[1] not in {"snapshot", "compare"}:
        print(__doc__, file=sys.stderr)
        return 2
    state = Path(argv[2])
    if argv[1] == "snapshot":
        state.write_text("\0".join(sorted(untracked_paths())))
        return 0

    before = {p for p in state.read_text().split("\0") if p}
    new = sorted(untracked_paths() - before)
    if not new:
        print("test litter check: no new untracked paths")
        return 0
    print(f"test litter check: the test run left {len(new)} new path(s) in the checkout:")
    for path in new:
        print(f"  {path!r}")
    print("Write to tmp_path, or rely on the isolated cwd/HOME in tests/conftest.py.")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
