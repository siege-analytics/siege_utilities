"""
Git workflow utilities for automated git operations and best practices.
Standardized workflows for feature development, releases, and hotfixes.
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

def validate_branch_naming(branch_name: str) -> Dict[str, Union[bool, str, List[str]]]:
    """Validate branch naming conventions."""
    
    # Common branch naming patterns
    patterns = {
        "feature": r"^feature/[a-z0-9-]+$",
        "bugfix": r"^bugfix/[a-z0-9-]+$",
        "hotfix": r"^hotfix/[a-z0-9-]+$",
        "release": r"^release/\d+\.\d+\.\d+$",
        "chore": r"^chore/[a-z0-9-]+$",
        "docs": r"^docs/[a-z0-9-]+$",
        "test": r"^test/[a-z0-9-]+$"
    }
    
    validation_results = {}
    matched_pattern = None
    
    for pattern_name, pattern in patterns.items():
        if re.match(pattern, branch_name):
            matched_pattern = pattern_name
            break
    
    # Check for common issues
    issues = []
    
    if not matched_pattern:
        issues.append("Branch name doesn't follow any standard pattern")
    
    if len(branch_name) > 50:
        issues.append("Branch name is too long (max 50 characters)")
    
    if branch_name.startswith('-') or branch_name.endswith('-'):
        issues.append("Branch name starts or ends with hyphen")
    
    if re.search(r'[A-Z]', branch_name):
        issues.append("Branch name contains uppercase letters (use lowercase)")
    
    if re.search(r'[^a-z0-9/-]', branch_name):
        issues.append("Branch name contains invalid characters")
    
    # Check for common prefixes
    valid_prefixes = ["feature", "bugfix", "hotfix", "release", "chore", "docs", "test"]
    prefix = branch_name.split('/')[0] if '/' in branch_name else ""
    
    if prefix and prefix not in valid_prefixes:
        issues.append(f"Unknown branch prefix: {prefix}")
    
    is_valid = len(issues) == 0
    
    return {
        "is_valid": is_valid,
        "matched_pattern": matched_pattern,
        "issues": issues,
        "suggestions": _generate_branch_suggestions(branch_name, issues)
    }

def _generate_branch_suggestions(branch_name: str, issues: List[str]) -> List[str]:
    """Generate suggestions for improving branch naming."""
    
    suggestions = []
    
    if "uppercase" in str(issues):
        suggestions.append(f"Use lowercase: {branch_name.lower()}")
    
    if "too long" in str(issues):
        suggestions.append("Keep branch names under 50 characters")
    
    if "invalid characters" in str(issues):
        suggestions.append("Use only lowercase letters, numbers, hyphens, and forward slashes")
    
    if "unknown prefix" in str(issues):
        suggestions.append("Use standard prefixes: feature/, bugfix/, hotfix/, release/, chore/, docs/, test/")
    
    # Suggest a better name if possible
    if not branch_name.startswith(('feature/', 'bugfix/', 'hotfix/', 'release/', 'chore/', 'docs/', 'test/')):
        if 'feature' in branch_name.lower():
            suggestions.append(f"feature/{branch_name.lower().replace('feature', '').strip('-/')}")
        elif 'bug' in branch_name.lower() or 'fix' in branch_name.lower():
            suggestions.append(f"bugfix/{branch_name.lower().replace('bug', '').replace('fix', '').strip('-/')}")
        elif 'hot' in branch_name.lower():
            suggestions.append(f"hotfix/{branch_name.lower().replace('hot', '').strip('-/')}")
        else:
            suggestions.append(f"feature/{branch_name.lower()}")
    
    return suggestions

def enforce_commit_conventions(commit_message: str) -> Dict[str, Union[bool, str, List[str]]]:
    """Enforce conventional commit message format."""
    
    # Conventional commit pattern
    conventional_pattern = r"^(feat|fix|docs|style|refactor|test|chore|perf|ci|build|revert)(\([a-z-]+\))?: .+"
    
    is_conventional = bool(re.match(conventional_pattern, commit_message))
    
    # Check for common issues
    issues = []
    
    if not is_conventional:
        issues.append("Commit message doesn't follow conventional format")
    
    if len(commit_message) > 72:
        issues.append("Commit message is too long (max 72 characters for first line)")
    
    if commit_message.startswith('WIP'):
        issues.append("Avoid 'WIP' in commit messages - use conventional format")
    
    if commit_message.lower().startswith('update') or commit_message.lower().startswith('change'):
        issues.append("Use specific conventional prefixes instead of generic words")
    
    # Check for imperative mood
    first_word = commit_message.split(':')[0].split('(')[-1] if ':' in commit_message else ""
    if first_word and first_word.endswith('s'):  # Simple check for imperative vs present tense
        issues.append("Use imperative mood (e.g., 'add' not 'adds')")
    
    is_valid = len(issues) == 0
    
    return {
        "is_valid": is_valid,
        "is_conventional": is_conventional,
        "issues": issues,
        "suggestions": _generate_commit_suggestions(commit_message, issues)
    }

def _generate_commit_suggestions(commit_message: str, issues: List[str]) -> List[str]:
    """Generate suggestions for improving commit messages."""
    
    suggestions = []
    
    if "conventional format" in str(issues):
        suggestions.append("Use format: type(scope): description")
        suggestions.append("Types: feat, fix, docs, style, refactor, test, chore, perf, ci, build, revert")
    
    if "too long" in str(issues):
        suggestions.append("Keep first line under 72 characters")
        suggestions.append("Use body for detailed explanation")
    
    if "generic words" in str(issues):
        suggestions.append("Instead of 'update', use: feat, fix, refactor, docs, etc.")
        suggestions.append("Instead of 'change', use: feat, fix, refactor, docs, etc.")
    
    if "imperative mood" in str(issues):
        suggestions.append("Use imperative mood: 'add', 'fix', 'update', 'remove'")
        suggestions.append("Not: 'adds', 'fixes', 'updates', 'removes'")
    
    # Suggest a conventional format
    if "conventional format" in str(issues):
        if 'fix' in commit_message.lower() or 'bug' in commit_message.lower():
            suggestions.append(f"fix: {commit_message.lower().replace('fix', '').replace('bug', '').strip()}")
        elif 'add' in commit_message.lower() or 'new' in commit_message.lower():
            suggestions.append(f"feat: {commit_message.lower().replace('add', '').replace('new', '').strip()}")
        elif 'update' in commit_message.lower():
            suggestions.append(f"refactor: {commit_message.lower().replace('update', '').strip()}")
        else:
            suggestions.append(f"feat: {commit_message}")
    
    return suggestions

def start_feature_workflow(
    feature_name: str,
    base_branch: str = "main",
    repo_path: str = ".",
    auto_push: bool = True
) -> Dict[str, Union[str, bool, Dict[str, str]]]:
    """Start a new feature development workflow."""
    
    # Validate feature name
    validation = validate_branch_naming(f"feature/{feature_name}")
    if not validation["is_valid"]:
        raise ValueError(f"Invalid feature name: {validation['issues']}")
    
    branch_name = f"feature/{feature_name}"
    
    try:
        # Ensure we're on base branch
        current_branch = run_git_command("branch", "--show-current", repo_path=repo_path)
        if current_branch != base_branch:
            run_git_command("checkout", base_branch, repo_path=repo_path)
            print(f"Switched to base branch: {base_branch}")
        
        # Pull latest changes
        run_git_command("pull", "origin", base_branch, repo_path=repo_path)
        print(f"Pulled latest changes from {base_branch}")
        
        # Create feature branch
        run_git_command("checkout", "-b", branch_name, repo_path=repo_path)
        print(f"Created feature branch: {branch_name}")
        
        # Push to remote if requested
        if auto_push:
            run_git_command("push", "-u", "origin", branch_name, repo_path=repo_path)
            print(f"Pushed feature branch to remote: origin/{branch_name}")
        
        return {
            "status": "success",
            "branch_name": branch_name,
            "base_branch": base_branch,
            "auto_push": auto_push,
            "workflow": "feature_started"
        }
        
    except Exception as e:
        return {
            "status": "failed",
            "error": str(e),
            "branch_name": branch_name,
            "base_branch": base_branch
        }

def complete_feature_workflow(
    feature_branch: str,
    target_branch: str = "main",
    repo_path: str = ".",
    squash: bool = True,
    delete_branch: bool = True
) -> Dict[str, Union[str, bool, Dict[str, str]]]:
    """Complete a feature development workflow."""
    
    try:
        # Ensure we're on target branch
        current_branch = run_git_command("branch", "--show-current", repo_path=repo_path)
        if current_branch != target_branch:
            run_git_command("checkout", target_branch, repo_path=repo_path)
            print(f"Switched to target branch: {target_branch}")
        
        # Pull latest changes
        run_git_command("pull", "origin", target_branch, repo_path=repo_path)
        print(f"Pulled latest changes from {target_branch}")
        
        # Merge feature branch
        merge_args = ["merge"]
        if squash:
            merge_args.append("--squash")
        
        merge_args.append(feature_branch)
        run_git_command(*merge_args, repo_path=repo_path)
        
        if squash:
            # Commit the squashed changes
            run_git_command("commit", "-m", f"feat: {feature_branch.replace('feature/', '')}")
        
        print(f"Successfully merged {feature_branch} into {target_branch}")
        
        # Push changes
        run_git_command("push", "origin", target_branch, repo_path=repo_path)
        print(f"Pushed changes to {target_branch}")
        
        # Delete feature branch if requested
        if delete_branch:
            # Delete local branch
            run_git_command("branch", "-d", feature_branch, repo_path=repo_path)
            print(f"Deleted local branch: {feature_branch}")
            
            # Delete remote branch
            try:
                run_git_command("push", "origin", "--delete", feature_branch, repo_path=repo_path)
                print(f"Deleted remote branch: origin/{feature_branch}")
            except:
                print(f"Could not delete remote branch: origin/{feature_branch}")
        
        return {
            "status": "success",
            "feature_branch": feature_branch,
            "target_branch": target_branch,
            "squash": squash,
            "delete_branch": delete_branch,
            "workflow": "feature_completed"
        }
        
    except Exception as e:
        return {
            "status": "failed",
            "error": str(e),
            "feature_branch": feature_branch,
            "target_branch": target_branch
        }

def hotfix_workflow(
    hotfix_name: str,
    base_branch: str = "main",
    repo_path: str = ".",
    auto_push: bool = True
) -> Dict[str, Union[str, bool, Dict[str, str]]]:
    """Start a hotfix workflow for urgent fixes."""
    
    # Validate hotfix name
    validation = validate_branch_naming(f"hotfix/{hotfix_name}")
    if not validation["is_valid"]:
        raise ValueError(f"Invalid hotfix name: {validation['issues']}")
    
    branch_name = f"hotfix/{hotfix_name}"
    
    try:
        # Ensure we're on base branch
        current_branch = run_git_command("branch", "--show-current", repo_path=repo_path)
        if current_branch != base_branch:
            run_git_command("checkout", base_branch, repo_path=repo_path)
            print(f"Switched to base branch: {base_branch}")
        
        # Pull latest changes
        run_git_command("pull", "origin", base_branch, repo_path=repo_path)
        print(f"Pulled latest changes from {base_branch}")
        
        # Create hotfix branch
        run_git_command("checkout", "-b", branch_name, repo_path=repo_path)
        print(f"Created hotfix branch: {branch_name}")
        
        # Push to remote if requested
        if auto_push:
            run_git_command("push", "-u", "origin", branch_name, repo_path=repo_path)
            print(f"Pushed hotfix branch to remote: origin/{branch_name}")
        
        return {
            "status": "success",
            "branch_name": branch_name,
            "base_branch": base_branch,
            "auto_push": auto_push,
            "workflow": "hotfix_started"
        }
        
    except Exception as e:
        return {
            "status": "failed",
            "error": str(e),
            "branch_name": branch_name,
            "base_branch": base_branch
        }

def release_workflow(
    version: str,
    base_branch: str = "main",
    repo_path: str = ".",
    auto_push: bool = True
) -> Dict[str, Union[str, bool, Dict[str, str]]]:
    """Start a release workflow for version releases."""
    
    # Validate version format (semantic versioning)
    if not re.match(r'^\d+\.\d+\.\d+$', version):
        raise ValueError(f"Invalid version format. Use semantic versioning (e.g., 1.0.0)")
    
    branch_name = f"release/{version}"
    
    try:
        # Ensure we're on base branch
        current_branch = run_git_command("branch", "--show-current", repo_path=repo_path)
        if current_branch != base_branch:
            run_git_command("checkout", base_branch, repo_path=repo_path)
            print(f"Switched to base branch: {base_branch}")
        
        # Pull latest changes
        run_git_command("pull", "origin", base_branch, repo_path=repo_path)
        print(f"Pulled latest changes from {base_branch}")
        
        # Create release branch
        run_git_command("checkout", "-b", branch_name, repo_path=repo_path)
        print(f"Created release branch: {branch_name}")
        
        # Update version files if they exist
        _update_version_files(version, repo_path)
        
        # Commit version changes
        run_git_command("add", ".", repo_path=repo_path)
        run_git_command("commit", "-m", f"chore: prepare release {version}", repo_path=repo_path)
        print(f"Committed version {version} changes")
        
        # Push to remote if requested
        if auto_push:
            run_git_command("push", "-u", "origin", branch_name, repo_path=repo_path)
            print(f"Pushed release branch to remote: origin/{branch_name}")
        
        return {
            "status": "success",
            "branch_name": branch_name,
            "version": version,
            "base_branch": base_branch,
            "auto_push": auto_push,
            "workflow": "release_started"
        }
        
    except Exception as e:
        return {
            "status": "failed",
            "error": str(e),
            "branch_name": branch_name,
            "version": version,
            "base_branch": base_branch
        }

def _update_version_files(version: str, repo_path: str) -> None:
    """Update common version files."""
    
    version_files = [
        "VERSION",
        "version.txt",
        "setup.py",
        "pyproject.toml",
        "package.json"
    ]
    
    for filename in version_files:
        file_path = Path(repo_path) / filename
        if file_path.exists():
            try:
                content = file_path.read_text()
                
                # Update version in different file formats
                if filename in ["VERSION", "version.txt"]:
                    file_path.write_text(version + "\n")
                elif filename == "setup.py":
                    content = re.sub(r"version=['\"][^'\"]*['\"]", f"version='{version}'", content)
                    file_path.write_text(content)
                elif filename == "pyproject.toml":
                    content = re.sub(r'version = "[^"]*"', f'version = "{version}"', content)
                    file_path.write_text(content)
                elif filename == "package.json":
                    content = re.sub(r'"version": "[^"]*"', f'"version": "{version}"', content)
                    file_path.write_text(content)
                
                print(f"Updated version in {filename}")
            except Exception as e:
                print(f"Warning: Could not update {filename}: {e}")

def get_workflow_status(repo_path: str = ".") -> Dict[str, Union[str, List[str], Dict[str, str]]]:
    """Get the current workflow status of the repository."""
    
    try:
        current_branch = run_git_command("branch", "--show-current", repo_path=repo_path)
        
        # Determine workflow type based on branch name
        if current_branch.startswith("feature/"):
            workflow_type = "feature_development"
            workflow_name = current_branch.replace("feature/", "")
        elif current_branch.startswith("hotfix/"):
            workflow_type = "hotfix"
            workflow_name = current_branch.replace("hotfix/", "")
        elif current_branch.startswith("release/"):
            workflow_type = "release"
            workflow_name = current_branch.replace("release/", "")
        elif current_branch in ["main", "master"]:
            workflow_type = "main_branch"
            workflow_name = current_branch
        else:
            workflow_type = "other"
            workflow_name = current_branch
        
        # Get workflow-specific information
        workflow_info = {
            "current_branch": current_branch,
            "workflow_type": workflow_type,
            "workflow_name": workflow_name,
            "status": "active"
        }
        
        if workflow_type in ["feature_development", "hotfix", "release"]:
            # Get ahead/behind info
            try:
                ahead_behind = run_git_command("rev-list", "--count", "--left-right", f"main...HEAD", repo_path=repo_path)
                behind, ahead = ahead_behind.split()
                workflow_info.update({
                    "commits_ahead": int(ahead),
                    "commits_behind": int(behind),
                    "ready_for_merge": int(ahead) > 0 and int(behind) == 0
                })
            except:
                workflow_info.update({
                    "commits_ahead": 0,
                    "commits_behind": 0,
                    "ready_for_merge": False
                })
        
        return workflow_info
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "current_branch": "unknown",
            "workflow_type": "unknown"
        }
