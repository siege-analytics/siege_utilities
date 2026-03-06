#!/usr/bin/env python3
"""
Compare two public API contract manifests and enforce compatibility policy.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Any, Dict, Set


@dataclass
class DiffResult:
    added_symbols: Set[str]
    removed_symbols: Set[str]
    signature_changes: Set[str]
    kind_changes: Set[str]


def load_json(path: str) -> Dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def diff_contracts(baseline: Dict[str, Any], candidate: Dict[str, Any]) -> DiffResult:
    base = baseline["symbols"]
    cand = candidate["symbols"]

    base_keys = set(base.keys())
    cand_keys = set(cand.keys())
    common = base_keys & cand_keys

    signature_changes = {
        name
        for name in common
        if (base[name].get("signature") or "") != (cand[name].get("signature") or "")
    }
    kind_changes = {
        name
        for name in common
        if (base[name].get("kind") or "") != (cand[name].get("kind") or "")
    }

    return DiffResult(
        added_symbols=cand_keys - base_keys,
        removed_symbols=base_keys - cand_keys,
        signature_changes=signature_changes,
        kind_changes=kind_changes,
    )


def apply_allowlist(diff: DiffResult, allowlist: Dict[str, Any]) -> DiffResult:
    added_ok = set(allowlist.get("added_symbols", []))
    removed_ok = set(allowlist.get("removed_symbols", []))
    signature_ok = set(allowlist.get("signature_changes", []))
    kind_ok = set(allowlist.get("kind_changes", []))

    return DiffResult(
        added_symbols=diff.added_symbols - added_ok,
        removed_symbols=diff.removed_symbols - removed_ok,
        signature_changes=diff.signature_changes - signature_ok,
        kind_changes=diff.kind_changes - kind_ok,
    )


def evaluate(diff: DiffResult, release_impact: str) -> tuple[bool, list[str]]:
    """
    Evaluate diff against release impact policy.

    patch:
      - no additions, removals, signature changes, or kind changes
    minor:
      - additions allowed
      - removals/signature/kind changes disallowed
    major:
      - additions allowed
      - removals/signature/kind changes allowed only when allowlisted
        (allowlist already applied before this function)
    """
    errors: list[str] = []

    if release_impact == "patch":
        if diff.added_symbols:
            errors.append(f"Patch release cannot add symbols: {sorted(diff.added_symbols)}")
        if diff.removed_symbols:
            errors.append(f"Patch release cannot remove symbols: {sorted(diff.removed_symbols)}")
        if diff.signature_changes:
            errors.append(
                "Patch release cannot change signatures: "
                f"{sorted(diff.signature_changes)}"
            )
        if diff.kind_changes:
            errors.append(f"Patch release cannot change symbol kind: {sorted(diff.kind_changes)}")
    elif release_impact == "minor":
        if diff.removed_symbols:
            errors.append(f"Minor release cannot remove symbols: {sorted(diff.removed_symbols)}")
        if diff.signature_changes:
            errors.append(
                "Minor release cannot change signatures: "
                f"{sorted(diff.signature_changes)}"
            )
        if diff.kind_changes:
            errors.append(f"Minor release cannot change symbol kind: {sorted(diff.kind_changes)}")
    elif release_impact == "major":
        if diff.removed_symbols:
            errors.append(
                "Major release has unallowlisted symbol removals: "
                f"{sorted(diff.removed_symbols)}"
            )
        if diff.signature_changes:
            errors.append(
                "Major release has unallowlisted signature changes: "
                f"{sorted(diff.signature_changes)}"
            )
        if diff.kind_changes:
            errors.append(
                "Major release has unallowlisted symbol-kind changes: "
                f"{sorted(diff.kind_changes)}"
            )
    else:
        errors.append(f"Unknown release impact: {release_impact}")

    return len(errors) == 0, errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare public API contract manifests.")
    parser.add_argument("--baseline", required=True, help="Baseline contract JSON path.")
    parser.add_argument("--candidate", required=True, help="Candidate contract JSON path.")
    parser.add_argument(
        "--release-impact",
        required=True,
        choices=["patch", "minor", "major"],
        help="Release impact policy level.",
    )
    parser.add_argument(
        "--allowlist",
        default="scripts/contracts/contract_allowlist.json",
        help="Optional allowlist JSON path.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    baseline = load_json(args.baseline)
    candidate = load_json(args.candidate)

    allowlist: Dict[str, Any] = {}
    try:
        allowlist = load_json(args.allowlist)
    except FileNotFoundError:
        allowlist = {}

    raw_diff = diff_contracts(baseline, candidate)
    filtered_diff = apply_allowlist(raw_diff, allowlist)
    ok, errors = evaluate(filtered_diff, args.release_impact)

    print(f"Baseline:  {baseline.get('package')}@{baseline.get('package_version')}")
    print(f"Candidate: {candidate.get('package')}@{candidate.get('package_version')}")
    print(f"Release impact policy: {args.release_impact}")
    print(f"Added symbols: {len(filtered_diff.added_symbols)}")
    print(f"Removed symbols: {len(filtered_diff.removed_symbols)}")
    print(f"Signature changes: {len(filtered_diff.signature_changes)}")
    print(f"Kind changes: {len(filtered_diff.kind_changes)}")

    if ok:
        print("API contract check: PASS")
        return 0

    print("API contract check: FAIL")
    for err in errors:
        print(f"- {err}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
