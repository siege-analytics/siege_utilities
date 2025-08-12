"""
Git status utilities for repository information and reporting.
Comprehensive repository state analysis and monitoring.
"""

import subprocess
import os
from pathlib import Path
from typing import List, Dict, Optional, Union
import re
from datetime import datetime

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

def get_repository_status(repo_path: str = ".") -> Dict[str, Union[str, int, bool]]:
    """Get comprehensive repository status information."""
    
    repo_path = Path(repo_path).resolve()
    
    if not (repo_path / ".git").exists():
        raise ValueError(f"Not a git repository: {repo_path}")
    
    # Basic repository info
    current_branch = run_git_command("branch", "--show-current", repo_path=repo_path)
    is_detached = "HEAD" in current_branch
    
    # Working directory status
    status_output = run_git_command("status", "--porcelain", repo_path=repo_path)
    status_lines = [line for line in status_output.split('\n') if line.strip()]
    
    # Count different types of changes
    staged_files = len([line for line in status_lines if line[0] in 'AMDR'])
    unstaged_files = len([line for line in status_lines if line[1] in 'AMDR'])
    untracked_files = len([line for line in status_lines if line.startswith('??')])
    
    # Get commit info
    try:
        last_commit_hash = run_git_command("rev-parse", "HEAD", repo_path=repo_path)[:7]
        last_commit_date = run_git_command("log", "-1", "--format=%cd", "--date=short", repo_path=repo_path)
        last_commit_author = run_git_command("log", "-1", "--format=%an", repo_path=repo_path)
        last_commit_message = run_git_command("log", "-1", "--format=%s", repo_path=repo_path)
    except:
        last_commit_hash = "unknown"
        last_commit_date = "unknown"
        last_commit_author = "unknown"
        last_commit_message = "unknown"
    
    # Get remote info
    try:
        remote_url = run_git_command("config", "--get", "remote.origin.url", repo_path=repo_path)
        upstream_branch = run_git_command("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}", repo_path=repo_path, check=False)
        if upstream_branch == "":
            upstream_branch = None
    except:
        remote_url = "unknown"
        upstream_branch = None
    
    # Get ahead/behind info
    ahead_behind = "0 0"
    if upstream_branch:
        try:
            ahead_behind = run_git_command("rev-list", "--count", "--left-right", f"{upstream_branch}...HEAD", repo_path=repo_path)
        except:
            ahead_behind = "0 0"
    
    behind, ahead = ahead_behind.split()
    
    return {
        "repository_path": str(repo_path),
        "current_branch": current_branch,
        "is_detached": is_detached,
        "staged_files": staged_files,
        "unstaged_files": unstaged_files,
        "untracked_files": untracked_files,
        "total_changes": staged_files + unstaged_files + untracked_files,
        "last_commit": {
            "hash": last_commit_hash,
            "date": last_commit_date,
            "author": last_commit_author,
            "message": last_commit_message
        },
        "remote": {
            "url": remote_url,
            "upstream_branch": upstream_branch,
            "ahead": int(ahead),
            "behind": int(behind)
        },
        "working_directory_clean": staged_files + unstaged_files + untracked_files == 0,
        "last_updated": datetime.now().isoformat()
    }

def get_branch_info(repo_path: str = ".") -> Dict[str, Union[str, List[str], int]]:
    """Get detailed information about all branches."""
    
    # Local branches
    local_branches = run_git_command("branch", "--list", "--format=%(refname:short)|%(upstream:short)|%(upstream:track)", repo_path=repo_path)
    
    branches = []
    for line in local_branches.split('\n'):
        if line.strip():
            parts = line.split('|')
            branch_name = parts[0]
            upstream = parts[1] if len(parts) > 1 and parts[1] else None
            tracking = parts[2] if len(parts) > 2 and parts[2] else None
            
            # Get branch details
            try:
                last_commit = run_git_command("log", "-1", "--format=%H|%cd|%an|%s", "--date=short", branch_name, repo_path=repo_path)
                if last_commit:
                    hash_part, date, author, message = last_commit.split('|', 3)
                    branches.append({
                        "name": branch_name,
                        "upstream": upstream,
                        "tracking": tracking,
                        "last_commit": {
                            "hash": hash_part[:7],
                            "date": date,
                            "author": author,
                            "message": message
                        }
                    })
            except:
                branches.append({
                    "name": branch_name,
                    "upstream": upstream,
                    "tracking": tracking,
                    "last_commit": None
                })
    
    # Remote branches
    remote_branches = run_git_command("branch", "-r", "--format=%(refname:short)", repo_path=repo_path)
    remote_branch_list = [branch.strip() for branch in remote_branches.split('\n') if branch.strip()]
    
    # Current branch
    current_branch = run_git_command("branch", "--show-current", repo_path=repo_path)
    
    return {
        "current_branch": current_branch,
        "local_branches": branches,
        "remote_branches": remote_branch_list,
        "total_local_branches": len(branches),
        "total_remote_branches": len(remote_branch_list)
    }

def get_remote_info(repo_path: str = ".") -> Dict[str, Union[str, List[Dict[str, str]]]]:
    """Get information about remote repositories."""
    
    # Get remote names
    remotes = run_git_command("remote", repo_path=repo_path)
    remote_list = [remote.strip() for remote in remotes.split('\n') if remote.strip()]
    
    remote_info = []
    for remote_name in remote_list:
        try:
            url = run_git_command("config", "--get", f"remote.{remote_name}.url", repo_path=repo_path)
            
            # Get fetch and push URLs if different
            fetch_url = run_git_command("config", "--get", f"remote.{remote_name}.fetch", repo_path=repo_path, check=False)
            push_url = run_git_command("config", "--get", f"remote.{remote_name}.push", repo_path=repo_path, check=False)
            
            remote_info.append({
                "name": remote_name,
                "url": url,
                "fetch_url": fetch_url if fetch_url else url,
                "push_url": push_url if push_url else url
            })
        except:
            remote_info.append({
                "name": remote_name,
                "url": "unknown",
                "fetch_url": "unknown",
                "push_url": "unknown"
            })
    
    return {
        "remotes": remote_info,
        "total_remotes": len(remote_info),
        "default_remote": "origin" if "origin" in remote_list else remote_list[0] if remote_list else None
    }

def get_stash_list(repo_path: str = ".") -> List[Dict[str, str]]:
    """Get list of stashed changes."""
    
    try:
        stash_output = run_git_command("stash", "list", "--format=%gd|%cd|%s", "--date=short", repo_path=repo_path)
        
        stashes = []
        for line in stash_output.split('\n'):
            if line.strip():
                parts = line.split('|', 2)
                if len(parts) == 3:
                    stash_ref, date, message = parts
                    stashes.append({
                        "ref": stash_ref,
                        "date": date,
                        "message": message
                    })
        
        return stashes
    except:
        return []

def get_tag_list(repo_path: str = ".") -> List[Dict[str, str]]:
    """Get list of tags with details."""
    
    try:
        tag_output = run_git_command("tag", "--format=%(refname:short)|%(creatordate:short)|%(creator)", repo_path=repo_path)
        
        tags = []
        for line in tag_output.split('\n'):
            if line.strip():
                parts = line.split('|', 2)
                if len(parts) == 3:
                    tag_name, date, author = parts
                    tags.append({
                        "name": tag_name,
                        "date": date,
                        "author": author
                    })
        
        return tags
    except:
        return []

def get_log_summary(
    since: Optional[str] = None,
    until: Optional[str] = None,
    author: Optional[str] = None,
    repo_path: str = ".",
    max_count: int = 100
) -> Dict[str, Union[int, List[Dict[str, str]]]]:
    """Get a summary of commit logs with filtering options."""
    
    log_args = ["log", f"--max-count={max_count}", "--format=%H|%cd|%an|%s", "--date=short"]
    
    if since:
        log_args.extend(["--since", since])
    if until:
        log_args.extend(["--until", until])
    if author:
        log_args.extend(["--author", author])
    
    try:
        log_output = run_git_command(*log_args, repo_path=repo_path)
        
        commits = []
        for line in log_output.split('\n'):
            if line.strip():
                parts = line.split('|', 3)
                if len(parts) == 4:
                    hash_full, date, author_name, message = parts
                    commits.append({
                        "hash": hash_full[:7],
                        "hash_full": hash_full,
                        "date": date,
                        "author": author_name,
                        "message": message
                    })
        
        return {
            "total_commits": len(commits),
            "commits": commits,
            "filters": {
                "since": since,
                "until": until,
                "author": author,
                "max_count": max_count
            }
        }
    except:
        return {
            "total_commits": 0,
            "commits": [],
            "filters": {
                "since": since,
                "until": until,
                "author": author,
                "max_count": max_count
            }
        }

def get_file_status(repo_path: str = ".") -> Dict[str, List[str]]:
    """Get detailed status of all files in the repository."""
    
    try:
        status_output = run_git_command("status", "--porcelain", repo_path=repo_path)
        
        files = {
            "staged": [],
            "unstaged": [],
            "untracked": [],
            "renamed": [],
            "deleted": []
        }
        
        for line in status_output.split('\n'):
            if line.strip():
                status = line[:2]
                filepath = line[3:]
                
                if status[0] == 'A':  # Added
                    files["staged"].append(filepath)
                elif status[0] == 'M':  # Modified
                    files["staged"].append(filepath)
                elif status[0] == 'D':  # Deleted
                    files["staged"].append(filepath)
                elif status[0] == 'R':  # Renamed
                    files["renamed"].append(filepath)
                elif status[1] == 'M':  # Modified (unstaged)
                    files["unstaged"].append(filepath)
                elif status[1] == 'D':  # Deleted (unstaged)
                    files["unstaged"].append(filepath)
                elif status == '??':  # Untracked
                    files["untracked"].append(filepath)
        
        return files
    except:
        return {
            "staged": [],
            "unstaged": [],
            "untracked": [],
            "renamed": [],
            "deleted": []
        }

def get_repository_size(repo_path: str = ".") -> Dict[str, Union[int, str]]:
    """Get repository size information."""
    
    repo_path = Path(repo_path).resolve()
    
    try:
        # Get .git directory size
        git_dir = repo_path / ".git"
        git_size = sum(f.stat().st_size for f in git_dir.rglob('*') if f.is_file())
        
        # Get working directory size (excluding .git)
        working_size = 0
        for f in repo_path.rglob('*'):
            if f.is_file() and '.git' not in f.parts:
                working_size += f.stat().st_size
        
        return {
            "git_directory_size_bytes": git_size,
            "git_directory_size_mb": round(git_size / (1024 * 1024), 2),
            "working_directory_size_bytes": working_size,
            "working_directory_size_mb": round(working_size / (1024 * 1024), 2),
            "total_size_bytes": git_size + working_size,
            "total_size_mb": round((git_size + working_size) / (1024 * 1024), 2)
        }
    except:
        return {
            "git_directory_size_bytes": 0,
            "git_directory_size_mb": 0,
            "working_directory_size_bytes": 0,
            "working_directory_size_mb": 0,
            "total_size_bytes": 0,
            "total_size_mb": 0
        }
