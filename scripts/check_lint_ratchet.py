#!/usr/bin/env python3
"""Lint ratchet checks for phases 2-4."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

PHASE1_RULES = "E722,F601,F403,F405"
PHASE2_RULES = "F401,F841,F541"
PHASE3_RULES = f"{PHASE1_RULES},{PHASE2_RULES}"
PHASE4_RULES = PHASE3_RULES
PHASE4_BASELINE = Path("lint_baselines/phase4_flake8_fingerprints.txt")
PHASE3_DOMAINS = [
    Path("siege_utilities/config"),
    Path("siege_utilities/geo"),
    Path("siege_utilities/files"),
]


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=True)


def git_changed_files(base_sha: str, head_sha: str) -> list[str]:
    cp = run(["git", "diff", "--name-only", f"{base_sha}..{head_sha}"])
    if cp.returncode != 0:
        raise RuntimeError(cp.stderr.strip() or "git diff failed")
    return [line.strip() for line in cp.stdout.splitlines() if line.strip()]


def resolve_base_head(base_sha: str | None, head_sha: str | None, base_ref: str) -> tuple[str, str]:
    if base_sha and head_sha:
        return base_sha, head_sha

    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    try:
        subprocess.run(["git", "fetch", "origin", "main", "--depth", "1"], check=False)
        base = subprocess.check_output(["git", "merge-base", base_ref, "HEAD"], text=True).strip()
        return base, head
    except Exception:
        parent = subprocess.check_output(["git", "rev-parse", "HEAD~1"], text=True).strip()
        return parent, head


def flake8_fingerprints(paths: list[str], select_rules: str) -> tuple[int, list[str], str]:
    if not paths:
        return 0, [], ""

    cmd = [
        "flake8",
        f"--select={select_rules}",
        "--format=%(path)s::%(code)s::%(text)s",
        *paths,
    ]
    cp = run(cmd)
    lines = [line.strip() for line in cp.stdout.splitlines() if line.strip()]
    return cp.returncode, sorted(set(lines)), cp.stderr.strip()


def check_phase2(base: str, head: str) -> int:
    changed = git_changed_files(base, head)
    touched_py = sorted({p for p in changed if p.endswith(".py") and Path(p).exists()})

    print("Phase 2 lint ratchet:")
    print(f"- Base: {base}")
    print(f"- Head: {head}")
    print(f"- Rules: {PHASE2_RULES}")

    if not touched_py:
        print("Phase 2: PASS (no touched Python files)")
        return 0

    _, issues, stderr = flake8_fingerprints(touched_py, PHASE2_RULES)
    if stderr:
        print(stderr)
    if not issues:
        print("Phase 2: PASS")
        return 0

    print("Phase 2: FAIL")
    for issue in issues[:200]:
        print(f"- {issue}")
    if len(issues) > 200:
        print(f"... and {len(issues) - 200} more")
    return 1


def check_phase3(base: str, head: str) -> int:
    changed = git_changed_files(base, head)
    touched_domains: list[Path] = []
    for domain in PHASE3_DOMAINS:
        prefix = f"{domain.as_posix()}/"
        if any(p.startswith(prefix) for p in changed):
            touched_domains.append(domain)

    print("Phase 3 lint ratchet:")
    print(f"- Base: {base}")
    print(f"- Head: {head}")
    print(f"- Rules: {PHASE3_RULES}")

    if not touched_domains:
        print("Phase 3: PASS (no touched high-change domains)")
        return 0

    failures = 0
    for domain in touched_domains:
        _, issues, _ = flake8_fingerprints([domain.as_posix()], PHASE3_RULES)
        if issues:
            failures += 1
            print(f"Phase 3 domain FAIL: {domain}")
            for issue in issues[:120]:
                print(f"- {issue}")
            if len(issues) > 120:
                print(f"... and {len(issues) - 120} more")
        else:
            print(f"Phase 3 domain PASS: {domain}")

    if failures:
        return 1

    print("Phase 3: PASS")
    return 0


def check_phase4(update_baseline: bool) -> int:
    print("Phase 4 lint ratchet:")
    print(f"- Rules: {PHASE4_RULES}")
    print(f"- Baseline: {PHASE4_BASELINE}")

    targets = ["siege_utilities", "tests", "scripts"]
    _, current, stderr = flake8_fingerprints(targets, PHASE4_RULES)
    if stderr:
        print(stderr)

    current_set = set(current)

    if update_baseline:
        PHASE4_BASELINE.parent.mkdir(parents=True, exist_ok=True)
        PHASE4_BASELINE.write_text("\n".join(sorted(current_set)) + ("\n" if current_set else ""))
        print(f"Phase 4 baseline updated with {len(current_set)} fingerprints")
        return 0

    if not PHASE4_BASELINE.exists():
        print("Phase 4: FAIL")
        print("- Baseline file missing.")
        print("- Generate it with: python scripts/check_lint_ratchet.py --phase phase4 --update-baseline")
        return 1

    baseline_set = {
        line.strip()
        for line in PHASE4_BASELINE.read_text().splitlines()
        if line.strip()
    }

    new_violations = sorted(current_set - baseline_set)
    resolved = sorted(baseline_set - current_set)

    print(f"- Baseline count: {len(baseline_set)}")
    print(f"- Current count: {len(current_set)}")
    print(f"- Resolved since baseline: {len(resolved)}")

    if not new_violations:
        print("Phase 4: PASS")
        return 0

    print("Phase 4: FAIL")
    print("New lint fingerprints introduced:")
    for issue in new_violations[:200]:
        print(f"- {issue}")
    if len(new_violations) > 200:
        print(f"... and {len(new_violations) - 200} more")
    print("\nFix guidance:")
    print("1) Resolve listed lint violations, or")
    print("2) If this is intentional temporary debt acceptance, update baseline in a dedicated debt-tracking PR.")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint ratchet checks for phases 2-4")
    parser.add_argument("--phase", required=True, choices=["phase2", "phase3", "phase4"])
    parser.add_argument("--base-sha", default="")
    parser.add_argument("--head-sha", default="")
    parser.add_argument("--base-ref", default="origin/main")
    parser.add_argument("--update-baseline", action="store_true")
    args = parser.parse_args()

    if args.phase == "phase4":
        return check_phase4(update_baseline=args.update_baseline)

    base, head = resolve_base_head(args.base_sha or None, args.head_sha or None, args.base_ref)

    if args.phase == "phase2":
        return check_phase2(base, head)
    if args.phase == "phase3":
        return check_phase3(base, head)

    print(f"Unknown phase: {args.phase}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
