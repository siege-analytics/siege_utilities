#!/usr/bin/env python3
"""
Retroactive commit-to-issue linking for siege_utilities.

Finds closed issues without commit SHA references and links them
to the commits/PRs that implemented them.

Usage:
    python scripts/link_commits_to_issues.py              # dry run
    python scripts/link_commits_to_issues.py --post       # post comments
    python scripts/link_commits_to_issues.py --json       # output JSON mapping
    python scripts/link_commits_to_issues.py --issue 215  # single issue
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class Commit:
    sha: str
    subject: str
    date: str  # ISO format

    @property
    def short_sha(self) -> str:
        return self.sha[:7]


@dataclass
class IssueMatch:
    issue_number: int
    title: str
    closed_at: str
    commits: list[Commit] = field(default_factory=list)
    prs: list[int] = field(default_factory=list)
    confidence: str = "low"  # high, medium, low
    strategy: str = ""  # pr, keyword, timeline, meta


# ---------------------------------------------------------------------------
# Shell helpers
# ---------------------------------------------------------------------------
def run(cmd: list[str], *, check: bool = True) -> str:
    """Run a command and return stdout."""
    result = subprocess.run(cmd, capture_output=True, text=True, check=check)
    return result.stdout.strip()


def gh_json(args: list[str]) -> list | dict:
    """Run a gh command and parse JSON output."""
    raw = run(["gh"] + args)
    if not raw:
        return []
    return json.loads(raw)


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------
def get_all_commits() -> list[Commit]:
    """Get all commits with SHA, subject, and date."""
    raw = run(
        ["git", "log", "--all", "--format=%H\t%s\t%aI"]
    )
    commits = []
    for line in raw.splitlines():
        parts = line.split("\t", 2)
        if len(parts) == 3:
            commits.append(Commit(sha=parts[0], subject=parts[1], date=parts[2]))
    return commits


def get_closed_issues(min_num: int = 157, max_num: int = 305) -> list[dict]:
    """Fetch closed issues in range."""
    issues = gh_json([
        "issue", "list",
        "--state", "closed",
        "--limit", "200",
        "--json", "number,title,closedAt,labels",
    ])
    return [
        i for i in issues
        if min_num <= i["number"] <= max_num
    ]


def get_issue_closing_prs(issue_number: int) -> list[dict]:
    """Get PRs that closed this issue."""
    try:
        data = gh_json([
            "issue", "view", str(issue_number),
            "--json", "closedByPullRequests",
        ])
        return data.get("closedByPullRequests", [])
    except subprocess.CalledProcessError:
        return []


def get_pr_merge_commit(pr_number: int) -> str | None:
    """Get merge commit SHA for a PR."""
    try:
        data = gh_json([
            "pr", "view", str(pr_number),
            "--json", "mergeCommit",
        ])
        mc = data.get("mergeCommit", {})
        return mc.get("oid") if mc else None
    except subprocess.CalledProcessError:
        return None


def get_pr_commits(pr_number: int) -> list[dict]:
    """Get commits in a PR."""
    try:
        data = gh_json([
            "pr", "view", str(pr_number),
            "--json", "commits",
        ])
        return data.get("commits", [])
    except subprocess.CalledProcessError:
        return []


def get_issue_comments(issue_number: int) -> list[dict]:
    """Get comments on an issue."""
    try:
        return gh_json([
            "issue", "view", str(issue_number),
            "--json", "comments",
            "--jq", ".comments",
        ])
    except subprocess.CalledProcessError:
        return []


# ---------------------------------------------------------------------------
# Detection: which issues already have commit references?
# ---------------------------------------------------------------------------
def issues_with_commit_refs_in_git(commits: list[Commit]) -> set[int]:
    """Find issue numbers referenced in commit messages via #N or su#N."""
    referenced = set()
    pattern = re.compile(r'(?:su)?#(\d+)')
    for c in commits:
        for m in pattern.finditer(c.subject):
            referenced.add(int(m.group(1)))
    return referenced


def issue_has_sha_in_comments(issue_number: int) -> bool:
    """Check if any comment on the issue already contains a commit SHA."""
    comments = get_issue_comments(issue_number)
    if not comments:
        return False
    sha_pattern = re.compile(r'[0-9a-f]{7,40}')
    for c in comments:
        body = c.get("body", "")
        if "Retroactive commit linkage" in body:
            return True  # already posted by this script
        # Look for actual commit-like references
        if sha_pattern.search(body) and ("commit" in body.lower() or "merge" in body.lower()):
            return True
    return False


# ---------------------------------------------------------------------------
# Matching strategies
# ---------------------------------------------------------------------------
def build_keyword_index(title: str) -> list[str]:
    """Extract searchable keywords from an issue title."""
    # Remove common filler words
    stop_words = {
        "add", "fix", "bug", "the", "for", "and", "with", "from", "into",
        "via", "all", "not", "can", "has", "use", "new", "old",
        "should", "must", "need", "update", "create", "make", "set",
        "get", "remove", "delete", "change", "move", "run", "test",
        "docs", "doc", "epic", "investigate", "still", "after",
    }
    # Clean and tokenize
    title_clean = re.sub(r'[^\w\s#-]', ' ', title.lower())
    # Also extract patterns like su#NNN
    tokens = title_clean.split()
    keywords = []
    for t in tokens:
        if t.startswith("su#"):
            continue
        if len(t) >= 3 and t not in stop_words:
            keywords.append(t)
    return keywords


def match_by_pr(issue_number: int, all_commits: list[Commit]) -> IssueMatch | None:
    """Try to match via closing PRs."""
    prs = get_issue_closing_prs(issue_number)
    if not prs:
        return None

    matched_commits = []
    pr_numbers = []
    for pr in prs:
        pr_num = pr.get("number")
        if not pr_num:
            continue
        pr_numbers.append(pr_num)
        merge_sha = get_pr_merge_commit(pr_num)
        if merge_sha:
            # Find the commit in our list
            for c in all_commits:
                if c.sha == merge_sha:
                    matched_commits.append(c)
                    break
            else:
                matched_commits.append(Commit(sha=merge_sha, subject=f"(merge commit for PR #{pr_num})", date=""))

        # Also get PR's own commits for richer context
        pr_commits = get_pr_commits(pr_num)
        for pc in pr_commits:
            sha = pc.get("oid", "")
            if sha and not any(mc.sha == sha for mc in matched_commits):
                for c in all_commits:
                    if c.sha == sha:
                        matched_commits.append(c)
                        break

    if matched_commits or pr_numbers:
        m = IssueMatch(
            issue_number=issue_number,
            title="",
            closed_at="",
            commits=matched_commits[:5],  # limit to 5 most relevant
            prs=pr_numbers,
            confidence="high",
            strategy="pr",
        )
        return m
    return None


def match_by_keyword(
    issue_number: int,
    title: str,
    closed_at: str,
    all_commits: list[Commit],
) -> IssueMatch | None:
    """Match by keyword similarity between issue title and commit messages."""
    keywords = build_keyword_index(title)
    if not keywords:
        return None

    # Parse close date for time window filtering
    try:
        close_dt = datetime.fromisoformat(closed_at.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        close_dt = None

    scored: list[tuple[int, Commit]] = []
    for c in all_commits:
        subj_lower = c.subject.lower()
        score = 0
        for kw in keywords:
            if kw in subj_lower:
                score += 1
                # Bonus for longer/rarer keywords
                if len(kw) >= 6:
                    score += 1

        if score >= 2:  # At least 2 keyword matches
            # Bonus for commits near the close date
            if close_dt and c.date:
                try:
                    commit_dt = datetime.fromisoformat(c.date)
                    delta = abs((close_dt - commit_dt).total_seconds())
                    if delta < 86400:  # within 1 day
                        score += 2
                    elif delta < 604800:  # within 1 week
                        score += 1
                except (ValueError, TypeError):
                    pass
            scored.append((score, c))

    if not scored:
        return None

    scored.sort(key=lambda x: x[0], reverse=True)
    best_score = scored[0][0]
    best_commits = [c for s, c in scored if s >= best_score - 1][:3]

    confidence = "high" if best_score >= 4 else "medium" if best_score >= 2 else "low"

    return IssueMatch(
        issue_number=issue_number,
        title="",
        closed_at="",
        commits=best_commits,
        confidence=confidence,
        strategy="keyword",
    )


def match_by_timeline(
    issue_number: int,
    closed_at: str,
    all_commits: list[Commit],
) -> IssueMatch | None:
    """Match by commits near the close date as last resort."""
    try:
        close_dt = datetime.fromisoformat(closed_at.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None

    # Find commits within 2 hours of closing
    nearby = []
    for c in all_commits:
        if not c.date:
            continue
        try:
            commit_dt = datetime.fromisoformat(c.date)
            delta = abs((close_dt - commit_dt).total_seconds())
            if delta < 7200:  # 2 hours
                nearby.append((delta, c))
        except (ValueError, TypeError):
            continue

    if not nearby:
        return None

    nearby.sort(key=lambda x: x[0])
    return IssueMatch(
        issue_number=issue_number,
        title="",
        closed_at="",
        commits=[c for _, c in nearby[:3]],
        confidence="low",
        strategy="timeline",
    )


# ---------------------------------------------------------------------------
# Meta/epic detection
# ---------------------------------------------------------------------------
EPIC_KEYWORDS = {"epic", "umbrella", "enabling", "adoption policy"}

# ---------------------------------------------------------------------------
# Manual overrides for issues where automated matching is inaccurate
# Maps issue number → (commit_shas, confidence, strategy_label)
# ---------------------------------------------------------------------------
MANUAL_OVERRIDES: dict[int, dict] = {
    272: {
        "shas": ["e568221"],
        "note": "Research/verification issue — Sedona spatial runtime planning contract covers the investigation",
        "confidence": "high",
        "strategy": "manual (reviewed keyword match)",
    },
    230: {
        "shas": ["8296544", "1017b25"],
        "note": "Boundary filtering fix + post-download filtering PR #199",
        "confidence": "high",
        "strategy": "manual (reviewed keyword match)",
    },
    229: {
        "shas": ["5985ca4", "80c1bf4", "973d199"],
        "note": "GDAL detection fix, plain PostgreSQL fallback, geo-no-gdal CI lane",
        "confidence": "high",
        "strategy": "manual (reviewed keyword match)",
    },
    204: {
        "shas": ["b89de11"],
        "note": "CI lanes, pytest markers, and CI release gate",
        "confidence": "high",
        "strategy": "manual (reviewed keyword match)",
    },
    189: {
        "shas": ["b89de11", "973d199", "be73dc2"],
        "note": "CI lanes + markers, geo-no-gdal lane creation and fix",
        "confidence": "high",
        "strategy": "manual (reviewed keyword match)",
    },
    179: {
        "shas": ["8296544"],
        "note": "Boundary filtering + demographics API call fix addressed alias propagation",
        "confidence": "high",
        "strategy": "manual (reviewed keyword match)",
    },
}


def is_meta_issue(title: str, labels: list[dict]) -> bool:
    """Detect epic/meta issues that aggregate sub-issues."""
    title_lower = title.lower()
    if any(kw in title_lower for kw in EPIC_KEYWORDS):
        return True
    label_names = {l.get("name", "").lower() for l in labels}
    if "epic" in label_names:
        return True
    return False


# ---------------------------------------------------------------------------
# Comment formatting
# ---------------------------------------------------------------------------
def format_comment(match: IssueMatch) -> str:
    """Format the comment to post on the issue."""
    lines = ["**Retroactive commit linkage**\n"]

    if match.prs:
        for pr_num in match.prs:
            lines.append(f"- PR #{pr_num}")

    if match.commits:
        for c in match.commits:
            lines.append(f"- `{c.short_sha}`: {c.subject}")

    conf_label = {
        "high": "high (PR linkage or strong keyword match)",
        "medium": "medium (keyword match)",
        "low": "low (timeline proximity)",
    }
    lines.append(f"\n_Confidence: {conf_label.get(match.confidence, match.confidence)}_")
    lines.append(f"_Strategy: {match.strategy}_")
    return "\n".join(lines)


def format_meta_comment(issue_number: int, title: str) -> str:
    """Format comment for meta/epic issues."""
    return (
        "**Retroactive commit linkage**\n\n"
        "This is an epic/meta issue that tracks sub-issues. "
        "Individual commits are linked on the respective sub-issues.\n\n"
        "_Confidence: high (meta-issue identification)_\n"
        "_Strategy: meta_"
    )


# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Link commits to closed issues")
    parser.add_argument("--post", action="store_true", help="Post comments (default: dry run)")
    parser.add_argument("--json", action="store_true", dest="json_output", help="Output JSON mapping")
    parser.add_argument("--issue", type=int, help="Process single issue number")
    parser.add_argument("--min", type=int, default=157, help="Minimum issue number")
    parser.add_argument("--max", type=int, default=305, help="Maximum issue number")
    parser.add_argument("--skip-comment-check", action="store_true",
                        help="Skip checking existing comments (faster)")
    args = parser.parse_args()

    print("Fetching commits...", file=sys.stderr)
    all_commits = get_all_commits()
    print(f"  {len(all_commits)} commits found", file=sys.stderr)

    # Find issues already referenced in commit messages
    already_referenced = issues_with_commit_refs_in_git(all_commits)
    print(f"  {len(already_referenced)} issues already referenced in commits", file=sys.stderr)

    print("Fetching closed issues...", file=sys.stderr)
    issues = get_closed_issues(args.min, args.max)
    print(f"  {len(issues)} closed issues in range #{args.min}-#{args.max}", file=sys.stderr)

    if args.issue:
        issues = [i for i in issues if i["number"] == args.issue]
        if not issues:
            print(f"Issue #{args.issue} not found in closed issues", file=sys.stderr)
            sys.exit(1)

    # Filter to unlinked issues
    unlinked = []
    for issue in issues:
        num = issue["number"]
        if num in already_referenced:
            continue
        unlinked.append(issue)

    print(f"  {len(unlinked)} issues need linking", file=sys.stderr)

    # Process each unlinked issue
    results: list[IssueMatch] = []
    for i, issue in enumerate(unlinked):
        num = issue["number"]
        title = issue["title"]
        closed_at = issue.get("closedAt", "")
        labels = issue.get("labels", [])

        print(f"\n[{i+1}/{len(unlinked)}] #{num}: {title}", file=sys.stderr)

        # Check if already has SHA in comments
        if not args.skip_comment_check and issue_has_sha_in_comments(num):
            print(f"  SKIP: already has commit reference in comments", file=sys.stderr)
            continue

        # Manual overrides (reviewed medium-confidence matches)
        if num in MANUAL_OVERRIDES:
            ovr = MANUAL_OVERRIDES[num]
            override_commits = []
            for sha_prefix in ovr["shas"]:
                for c in all_commits:
                    if c.sha.startswith(sha_prefix):
                        override_commits.append(c)
                        break
                else:
                    # Commit not in local history — record with prefix only
                    override_commits.append(Commit(sha=sha_prefix, subject=ovr.get("note", ""), date=""))
            match = IssueMatch(
                issue_number=num,
                title=title,
                closed_at=closed_at,
                commits=override_commits,
                confidence=ovr["confidence"],
                strategy=ovr["strategy"],
            )
            results.append(match)
            shas = ", ".join(c.short_sha for c in override_commits)
            print(f"  OVERRIDE ({ovr['confidence']}): {shas}", file=sys.stderr)
            continue

        # Meta/epic issues
        if is_meta_issue(title, labels):
            match = IssueMatch(
                issue_number=num,
                title=title,
                closed_at=closed_at,
                confidence="high",
                strategy="meta",
            )
            results.append(match)
            print(f"  META: epic/umbrella issue", file=sys.stderr)
            continue

        # Strategy 1: PR linkage
        match = match_by_pr(num, all_commits)
        if match:
            match.issue_number = num
            match.title = title
            match.closed_at = closed_at
            results.append(match)
            pr_str = ", ".join(f"#{p}" for p in match.prs)
            print(f"  PR: {pr_str} ({len(match.commits)} commits)", file=sys.stderr)
            continue

        # Strategy 2: Keyword match
        match = match_by_keyword(num, title, closed_at, all_commits)
        if match:
            match.issue_number = num
            match.title = title
            match.closed_at = closed_at
            results.append(match)
            shas = ", ".join(c.short_sha for c in match.commits)
            print(f"  KEYWORD ({match.confidence}): {shas}", file=sys.stderr)
            continue

        # Strategy 3: Timeline
        match = match_by_timeline(num, closed_at, all_commits)
        if match:
            match.issue_number = num
            match.title = title
            match.closed_at = closed_at
            results.append(match)
            shas = ", ".join(c.short_sha for c in match.commits)
            print(f"  TIMELINE (low): {shas}", file=sys.stderr)
            continue

        print(f"  NO MATCH", file=sys.stderr)

    # Output
    print(f"\n{'='*60}", file=sys.stderr)
    print(f"Results: {len(results)} issues matched", file=sys.stderr)
    by_confidence = {}
    for r in results:
        by_confidence.setdefault(r.confidence, []).append(r)
    for conf in ["high", "medium", "low"]:
        count = len(by_confidence.get(conf, []))
        if count:
            print(f"  {conf}: {count}", file=sys.stderr)

    if args.json_output:
        mapping = {}
        for r in results:
            mapping[r.issue_number] = {
                "title": r.title,
                "commits": [{"sha": c.sha, "subject": c.subject} for c in r.commits],
                "prs": r.prs,
                "confidence": r.confidence,
                "strategy": r.strategy,
            }
        print(json.dumps(mapping, indent=2))
        return

    # Print dry run or post
    for r in results:
        if r.strategy == "meta":
            comment = format_meta_comment(r.issue_number, r.title)
        else:
            comment = format_comment(r)

        if args.post:
            print(f"\nPosting comment on #{r.issue_number}...", file=sys.stderr)
            try:
                run(["gh", "issue", "comment", str(r.issue_number), "--body", comment])
                print(f"  POSTED", file=sys.stderr)
            except subprocess.CalledProcessError as e:
                print(f"  FAILED: {e}", file=sys.stderr)
        else:
            print(f"\n--- #{r.issue_number}: {r.title} ---")
            print(f"Confidence: {r.confidence} | Strategy: {r.strategy}")
            print(comment)
            print()


if __name__ == "__main__":
    main()
