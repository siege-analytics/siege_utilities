#!/usr/bin/env python3
"""Run Bandit security scanner on siege_utilities and report findings.

Usage:
    python scripts/check_security.py                  # fail on high/medium
    python scripts/check_security.py --update-baseline  # capture current state
    python scripts/check_security.py --severity high    # only high severity

Reads Bandit configuration from [tool.bandit] in pyproject.toml.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

BASELINE_FILE = Path("security_baselines/bandit_baseline.json")
TARGETS = ["siege_utilities"]


def run_bandit(severity: str) -> tuple[int, list[dict], str]:
    """Run Bandit and return (exit_code, results, stderr)."""
    sev_flag = {"low": "l", "medium": "m", "high": "h"}[severity]
    cmd = [
        "bandit",
        "-r",
        *TARGETS,
        f"-{'i' * 1}{sev_flag}",
        "-f", "json",
        "-c", "pyproject.toml",
        "--quiet",
    ]
    cp = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    results = []
    if cp.stdout.strip():
        try:
            data = json.loads(cp.stdout)
            results = data.get("results", [])
        except (json.JSONDecodeError, ValueError):
            pass
    return cp.returncode, results, cp.stderr.strip()


def fingerprint(finding: dict) -> str:
    """Stable fingerprint for deduplication against baseline."""
    return f"{finding.get('filename', '')}::{finding.get('test_id', '')}::{finding.get('line_number', '')}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Bandit security scan for siege_utilities.")
    parser.add_argument(
        "--severity", choices=["low", "medium", "high"], default="medium",
        help="Minimum severity to report (default: medium)",
    )
    parser.add_argument(
        "--update-baseline", action="store_true",
        help="Save current findings as the baseline",
    )
    args = parser.parse_args()

    try:
        subprocess.run(["bandit", "--version"], capture_output=True, check=True, timeout=10)
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("Security scan: FAIL")
        print("- bandit is not installed. Install: pip install bandit")
        return 1

    exit_code, results, stderr = run_bandit(args.severity)
    if stderr:
        print(stderr, file=sys.stderr)

    current_fps = {fingerprint(r) for r in results}

    if args.update_baseline:
        BASELINE_FILE.parent.mkdir(parents=True, exist_ok=True)
        baseline_data = {
            "fingerprints": sorted(current_fps),
            "count": len(current_fps),
            "severity": args.severity,
        }
        BASELINE_FILE.write_text(json.dumps(baseline_data, indent=2) + "\n")
        print(f"Security baseline updated: {len(current_fps)} findings at severity >= {args.severity}")
        return 0

    if BASELINE_FILE.exists():
        baseline = json.loads(BASELINE_FILE.read_text())
        baseline_fps = set(baseline.get("fingerprints", []))
    else:
        baseline_fps = set()

    new_findings = current_fps - baseline_fps
    resolved = baseline_fps - current_fps

    print(f"Security scan (severity >= {args.severity}):")
    print(f"- Current findings: {len(current_fps)}")
    print(f"- Baseline findings: {len(baseline_fps)}")
    print(f"- New since baseline: {len(new_findings)}")
    print(f"- Resolved since baseline: {len(resolved)}")

    if new_findings:
        print("\nNew security findings:")
        for r in results:
            if fingerprint(r) in new_findings:
                print(f"  [{r.get('issue_severity', '?')}] {r.get('filename', '?')}:{r.get('line_number', '?')}")
                print(f"    {r.get('test_id', '')}: {r.get('issue_text', '')}")
        print("\nSecurity scan: FAIL")
        print("Fix the new findings or update the baseline with --update-baseline")
        return 1

    print("\nSecurity scan: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
