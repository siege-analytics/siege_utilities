#!/usr/bin/env python3
"""Phase 1 lint ratchet gate: enforce severe rules on touched Python files."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

SEVERE_RULES = "E722,F601,F403,F405"


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=True)


def _resolve_base_head(base_sha: str | None, head_sha: str | None, base_ref: str) -> tuple[str, str]:
    if base_sha and head_sha:
        return base_sha, head_sha

    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()

    try:
        ref = base_ref
        remote = "origin"
        if "/" in base_ref:
            remote, ref = base_ref.split("/", 1)
        subprocess.run(["git", "fetch", remote, ref, "--depth", "1"], check=False)
        merge_base = subprocess.check_output(["git", "merge-base", base_ref, "HEAD"], text=True).strip()
        return merge_base, head
    except Exception:
        parent = subprocess.check_output(["git", "rev-parse", "HEAD~1"], text=True).strip()
        return parent, head


def changed_python_files(base: str, head: str) -> list[str]:
    cp = run(["git", "diff", "--name-only", f"{base}..{head}"])
    if cp.returncode != 0:
        raise RuntimeError(cp.stderr.strip() or "git diff failed")

    files: list[str] = []
    for raw in cp.stdout.splitlines():
        path = raw.strip()
        if not path.endswith(".py"):
            continue
        if not Path(path).exists():
            continue
        files.append(path)
    return sorted(set(files))


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 1 lint ratchet for touched Python files.")
    parser.add_argument("--base-sha", default="", help="Base SHA (optional).")
    parser.add_argument("--head-sha", default="", help="Head SHA (optional).")
    parser.add_argument("--base-ref", default="origin/main", help="Base ref fallback (default: origin/main).")
    parser.add_argument("--select", default=SEVERE_RULES, help="Flake8 rules to enforce.")
    args = parser.parse_args()

    if shutil.which("flake8") is None:
        print("Phase 1 lint ratchet: FAIL")
        print("- flake8 is not installed in this environment.")
        print("- Install and rerun: pip install flake8")
        return 1

    base, head = _resolve_base_head(args.base_sha or None, args.head_sha or None, args.base_ref)
    files = changed_python_files(base, head)

    if not files:
        print("Phase 1 lint ratchet: PASS")
        print("No touched Python files in diff; gate skipped.")
        return 0

    print("Phase 1 lint ratchet scope:")
    print(f"- Base: {base}")
    print(f"- Head: {head}")
    print(f"- Rules: {args.select}")
    print(f"- Files: {len(files)}")

    cmd = ["flake8", f"--select={args.select}", "--show-source", "--statistics", *files]
    cp = run(cmd)

    if cp.returncode == 0:
        print("Phase 1 lint ratchet: PASS")
        return 0

    print("Phase 1 lint ratchet: FAIL")
    if cp.stdout.strip():
        print(cp.stdout.strip())
    if cp.stderr.strip():
        print(cp.stderr.strip())

    print("\nHow to fix locally:")
    print("1) Fix listed violations in touched Python files.")
    print("2) Re-run: python scripts/check_lint_ratchet_phase1.py")
    print("3) See policy: LINT_RATCHET_PLAN.md (Phase 1)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
