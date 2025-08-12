"""
Branch analysis utilities for git repositories.
Based on the Change-Agent-AI branch status generator.
"""

import os
import subprocess
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import json

def run_git_command(*args, repo_path: str = ".", check: bool = True) -> str:
    """Run a git command and return the output."""
    try:
        result = subprocess.run(
            ["git"] + list(args),
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=check
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        if check:
            raise RuntimeError(f"Git command failed: {' '.join(args)} - {e.stderr}")
        return ""

def analyze_branch_status(repo_path: str = ".") -> Dict[str, str]:
    """Analyze the current branch status."""
    repo_path = Path(repo_path).resolve()
    
    if not (repo_path / ".git").exists():
        raise ValueError(f"Not a git repository: {repo_path}")
    
    current_branch = run_git_command("branch", "--show-current", repo_path=repo_path)
    
    # Get commits ahead/behind main
    try:
        status_output = run_git_command("rev-list", "--count", "--left-right", "main...HEAD", repo_path=repo_path)
        if status_output:
            behind, ahead = status_output.split()
        else:
            behind, ahead = "0", "0"
    except:
        behind, ahead = "0", "0"
    
    # Get last commit info
    last_commit_hash = run_git_command("rev-parse", "HEAD", repo_path=repo_path)[:7]
    last_commit_date = run_git_command("log", "-1", "--format=%cd", "--date=short", repo_path=repo_path)
    last_commit_msg = run_git_command("log", "-1", "--format=%s", repo_path=repo_path)
    
    return {
        "branch": current_branch,
        "ahead": ahead,
        "behind": behind,
        "last_commit_hash": last_commit_hash,
        "last_commit_date": last_commit_date,
        "last_commit_msg": last_commit_msg,
        "repo_path": str(repo_path)
    }

def get_commit_history(limit: int = 20, repo_path: str = ".") -> List[Dict[str, str]]:
    """Get recent commit history with details."""
    commits = []
    
    # Get commit log with hash, date, author, and message
    log_output = run_git_command(
        "log", f"--max-count={limit}",
        "--format=%H|%cd|%an|%s",
        "--date=short",
        repo_path=repo_path
    )
    
    for line in log_output.split('\n'):
        if line.strip():
            parts = line.split('|', 3)
            if len(parts) == 4:
                hash_full, date, author, message = parts
                commits.append({
                    "hash": hash_full[:7],
                    "hash_full": hash_full,
                    "date": date,
                    "author": author,
                    "message": message
                })
    
    return commits

def categorize_commits(commits: List[Dict[str, str]]) -> Dict[str, List[Dict[str, str]]]:
    """Categorize commits by type and purpose."""
    categories = {
        "features": [],
        "fixes": [],
        "docs": [],
        "refactor": [],
        "infrastructure": [],
        "other": []
    }
    
    for commit in commits:
        message = commit["message"].lower()
        
        if any(word in message for word in ["feat", "feature", "add", "implement"]):
            categories["features"].append(commit)
        elif any(word in message for word in ["fix", "bug", "resolve", "correct"]):
            categories["fixes"].append(commit)
        elif any(word in message for word in ["doc", "readme", "comment"]):
            categories["docs"].append(commit)
        elif any(word in message for word in ["refactor", "clean", "improve", "optimize"]):
            categories["refactor"].append(commit)
        elif any(word in message for word in ["docker", "makefile", "script", "config", "build"]):
            categories["infrastructure"].append(commit)
        else:
            categories["other"].append(commit)
    
    return categories

def get_file_changes(repo_path: str = ".") -> Dict[str, List[str]]:
    """Get files that differ from main branch."""
    try:
        # Get list of changed files
        changed_files = run_git_command("diff", "--name-status", "main...HEAD", repo_path=repo_path)
        
        added = []
        modified = []
        deleted = []
        
        for line in changed_files.split('\n'):
            if line.strip():
                status, filepath = line.split('\t', 1)
                if status == 'A':
                    added.append(filepath)
                elif status == 'M':
                    modified.append(filepath)
                elif status == 'D':
                    deleted.append(filepath)
        
        return {
            "added": added,
            "modified": modified,
            "deleted": deleted
        }
    except:
        return {"added": [], "modified": [], "deleted": []}

def get_file_stats(repo_path: str = ".") -> Dict[str, int]:
    """Get statistics about file changes."""
    diff_stats = run_git_command("diff", "--stat", "main...HEAD", repo_path=repo_path)
    
    # Parse the stat output to get line counts
    lines_added = 0
    lines_deleted = 0
    
    for line in diff_stats.split('\n'):
        if '|' in line and 'insertions' in line:
            # Extract numbers from lines like " 3 files changed, 45 insertions(+), 12 deletions(-)"
            match = re.search(r'(\d+) insertions?\(\+\), (\d+) deletions?\(-\)', line)
            if match:
                lines_added = int(match.group(1))
                lines_deleted = int(match.group(2))
            break
    
    return {
        "lines_added": lines_added,
        "lines_deleted": lines_deleted
    }

def generate_branch_report(
    output_file: Optional[str] = None,
    repo_path: str = ".",
    include_commits: int = 20
) -> str:
    """Generate a comprehensive branch status report."""
    
    # Get all the data
    status = analyze_branch_status(repo_path)
    commits = get_commit_history(include_commits, repo_path)
    categories = categorize_commits(commits)
    diff_info = get_file_changes(repo_path)
    file_stats = get_file_stats(repo_path)
    
    # Generate the report
    current_date = datetime.now().strftime("%B %d, %Y")
    
    # Determine status emoji and text
    if int(status["ahead"]) > 0:
        status_emoji = "🚀"
        status_text = "IN DEVELOPMENT"
    else:
        status_emoji = "✅"
        status_text = "READY FOR MERGE"
    
    # Header
    report = f"""# Feature Branch Status: `{status['branch']}`

**Branch**: `{status['branch']}`  
**Last Updated**: {current_date}  
**Status**: {status_emoji} **{status_text}**  
**Ahead of main**: {status['ahead']} commits  
**Behind main**: {status['behind']} commits  

**Last Commit**: `{status['last_commit_hash']}` on {status['last_commit_date']}  
**Message**: {status['last_commit_msg']}"""

    # Overview
    report += f"""

## 🎯 **Branch Overview**

This branch represents ongoing development work with **{status['ahead']} commits ahead** of the main branch.

**Change Statistics:**
- **Lines Added**: {file_stats['lines_added']:,}
- **Lines Deleted**: {file_stats['lines_deleted']:,}
- **Net Change**: {file_stats['lines_added'] - file_stats['lines_deleted']:,} lines"""

    # Commit History
    report += """

## 📋 **Complete Commit History**

### **Latest Commits (Most Recent First)**

| Commit | Date | Author | Description |
|--------|------|--------|-------------|"""

    # Show recent commits in table
    for commit in commits[:10]:  # Show last 10 commits
        report += f"""
| `{commit['hash']}` | {commit['date']} | {commit['author']} | {commit['message']} |"""

    report += "\n\n### **Commit Categories**\n"
    
    # Show categorized commits
    for category, category_commits in categories.items():
        if category_commits:
            report += f"\n#### **{category.title()}** ({len(category_commits)} commits)\n"
            for commit in category_commits[:5]:  # Show up to 5 per category
                report += f"- **`{commit['hash']}`** ({commit['date']}): {commit['message']}\n"
            if len(category_commits) > 5:
                report += f"- ... and {len(category_commits) - 5} more\n"

    # File Changes
    report += """

## 📁 **File Changes**

### **Files Added**"""
    
    if diff_info["added"]:
        for file_path in sorted(diff_info["added"]):
            report += f"\n- `{file_path}`"
    else:
        report += "\n- No new files added"
    
    report += "\n\n### **Files Modified**"
    if diff_info["modified"]:
        for file_path in sorted(diff_info["modified"]):
            report += f"\n- `{file_path}`"
    else:
        report += "\n- No files modified"
    
    report += "\n\n### **Files Deleted**"
    if diff_info["deleted"]:
        for file_path in sorted(diff_info["deleted"]):
            report += f"\n- `{file_path}`"
    else:
        report += "\n- No files deleted"
    
    # Next Steps
    report += """

## 📚 **Next Steps**

### **Immediate Actions**
1. **Code Review** - Review changes and ensure quality
2. **Testing** - Verify functionality in development environment
3. **Documentation** - Update any related documentation
4. **Pull Request** - Create PR when ready for review

### **Future Considerations**
1. **Integration Testing** - End-to-end testing with other components
2. **Performance Review** - Ensure changes don't impact performance
3. **Security Review** - Verify security implications of changes
4. **Deployment Planning** - Plan production deployment strategy"""

    # Footer
    report += f"""

## 🔗 **Related Resources**

- **Local Repository**: `{status['repo_path']}`
- **Branch Status**: `git status` in repository directory

---

**Branch Maintainer**: Development Team  
**Last Generated**: {datetime.now().strftime("%B %d, %Y at %I:%M %p")}  
**Status**: {'🚀 IN DEVELOPMENT' if int(status['ahead']) > 0 else '✅ READY FOR MERGE'}"""

    # Save to file if specified
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"✅ Branch report saved to: {output_file}")
    
    return report
