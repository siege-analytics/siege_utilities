"""
Git operations utilities for repository management.
Comprehensive git commands and workflow automation.
"""

import subprocess
from typing import Dict, Optional
import re

from siege_utilities.core.logging import log_info, log_warning, log_error
from siege_utilities.exceptions import GitError

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
            raise GitError(f"Git command failed: {' '.join(args)} - {e.stderr}")
        return ""

def create_feature_branch(
    branch_name: str,
    base_branch: str = "main",
    repo_path: str = ".",
    switch_to_branch: bool = True
) -> Dict[str, str]:
    """Create a new feature branch from base branch."""

    # Validate branch name
    if not re.match(r'^[a-zA-Z0-9/_-]+$', branch_name):
        raise ValueError(f"Invalid branch name: {branch_name}")

    # Check if we're on the base branch
    current_branch = run_git_command("branch", "--show-current", repo_path=repo_path)
    if current_branch != base_branch:
        # Switch to base branch first
        run_git_command("checkout", base_branch, repo_path=repo_path)
        log_info(f"Switched to base branch: {base_branch}")

    # Pull latest changes if remote exists
    remotes = run_git_command("remote", repo_path=repo_path, check=False)
    if remotes and "origin" in remotes:
        try:
            run_git_command("pull", "origin", base_branch, repo_path=repo_path, check=False)
            log_info(f"Pulled latest changes from {base_branch}")
        except Exception:
            pass  # Pull failed, continue anyway

    # Create and switch to new branch
    run_git_command("checkout", "-b", branch_name, repo_path=repo_path)
    log_info(f"Created and switched to feature branch: {branch_name}")

    # Push to remote if switch_to_branch is True and remote exists
    if switch_to_branch and remotes and "origin" in remotes:
        try:
            run_git_command("push", "-u", "origin", branch_name, repo_path=repo_path, check=False)
            log_info(f"Pushed branch to remote: origin/{branch_name}")
        except Exception:
            log_warning(f"Could not push to remote (continuing anyway)")

    return {
        "branch_name": branch_name,
        "base_branch": base_branch,
        "status": "created",
        "remote_tracking": switch_to_branch
    }

def switch_branch(branch_name: str, repo_path: str = ".") -> Dict[str, str]:
    """
    Switch to an existing branch.

    SECURITY: Validates branch names to prevent command injection.

    Args:
        branch_name: Name of branch to switch to
        repo_path: Repository path

    Returns:
        Dictionary with switch status

    Raises:
        GitSecurityError: If branch name fails validation
    """
    # Validate inputs
    try:
        from siege_utilities.git.validation import validate_branch_name, validate_repo_path
        branch_name = validate_branch_name(branch_name)
        repo_path = str(validate_repo_path(repo_path))
    except ImportError:
        pass

    # Check if branch exists
    branches = run_git_command("branch", "--list", repo_path=repo_path)
    if branch_name not in branches:
        # Check remote branches
        remote_branches = run_git_command("branch", "-r", repo_path=repo_path)
        if f"origin/{branch_name}" in remote_branches:
            # Create local tracking branch
            run_git_command("checkout", "-b", branch_name, f"origin/{branch_name}", repo_path=repo_path)
        else:
            raise ValueError(f"Branch {branch_name} does not exist locally or remotely")
    else:
        run_git_command("checkout", branch_name, repo_path=repo_path)

    # Get current status
    current_branch = run_git_command("branch", "--show-current", repo_path=repo_path)

    return {
        "previous_branch": "unknown",  # Could be enhanced to track previous branch
        "current_branch": current_branch,
        "status": "switched"
    }

def merge_branch(
    source_branch: str,
    target_branch: str = "main",
    repo_path: str = ".",
    fast_forward_only: bool = False,
    squash: bool = False
) -> Dict[str, str]:
    """
    Merge a source branch into target branch.

    SECURITY: Validates branch names to prevent command injection.

    Args:
        source_branch: Branch to merge from
        target_branch: Branch to merge into
        repo_path: Repository path
        fast_forward_only: Only allow fast-forward merges
        squash: Squash commits during merge

    Returns:
        Dictionary with merge status

    Raises:
        GitSecurityError: If branch names fail validation
    """
    # Validate inputs
    try:
        from siege_utilities.git.validation import validate_branch_name, validate_repo_path
        source_branch = validate_branch_name(source_branch)
        target_branch = validate_branch_name(target_branch)
        repo_path = str(validate_repo_path(repo_path))
    except ImportError:
        pass

    # Switch to target branch
    current_branch = run_git_command("branch", "--show-current", repo_path=repo_path)
    if current_branch != target_branch:
        run_git_command("checkout", target_branch, repo_path=repo_path)
        log_info(f"Switched to target branch: {target_branch}")

    # Pull latest changes
    run_git_command("pull", "origin", target_branch, repo_path=repo_path)

    # Prepare merge command
    merge_args = ["merge"]
    if fast_forward_only:
        merge_args.append("--ff-only")
    if squash:
        merge_args.append("--squash")

    merge_args.append(source_branch)

    # Execute merge
    try:
        run_git_command(*merge_args, repo_path=repo_path)
        merge_status = "success"
        log_info(f"Successfully merged {source_branch} into {target_branch}")
    except (RuntimeError, GitError) as e:
        merge_status = "failed"
        log_error(f"Merge failed: {e}")
        return {"status": merge_status, "error": str(e)}

    return {
        "source_branch": source_branch,
        "target_branch": target_branch,
        "status": merge_status,
        "fast_forward_only": fast_forward_only,
        "squash": squash
    }

def rebase_branch(
    source_branch: str,
    base_branch: str = "main",
    repo_path: str = ".",
    interactive: bool = False
) -> Dict[str, str]:
    """
    Rebase a branch onto another branch.

    SECURITY: Validates branch names to prevent command injection.

    Args:
        source_branch: Branch to rebase
        base_branch: Branch to rebase onto
        repo_path: Repository path
        interactive: Use interactive rebase

    Returns:
        Dictionary with rebase status

    Raises:
        GitSecurityError: If branch names fail validation
    """
    # Validate inputs
    try:
        from siege_utilities.git.validation import validate_branch_name, validate_repo_path
        source_branch = validate_branch_name(source_branch)
        base_branch = validate_branch_name(base_branch)
        repo_path = str(validate_repo_path(repo_path))
    except ImportError:
        pass

    # Switch to source branch
    current_branch = run_git_command("branch", "--show-current", repo_path=repo_path)
    if current_branch != source_branch:
        run_git_command("checkout", source_branch, repo_path=repo_path)
        log_info(f"Switched to source branch: {source_branch}")

    # Prepare rebase command
    rebase_args = ["rebase"]
    if interactive:
        rebase_args.append("-i")

    rebase_args.append(base_branch)

    # Execute rebase
    try:
        run_git_command(*rebase_args, repo_path=repo_path)
        rebase_status = "success"
        log_info(f"Successfully rebased {source_branch} onto {base_branch}")
    except (RuntimeError, GitError) as e:
        rebase_status = "failed"
        log_error(f"Rebase failed: {e}")
        return {"status": rebase_status, "error": str(e)}

    return {
        "source_branch": source_branch,
        "base_branch": base_branch,
        "status": rebase_status,
        "interactive": interactive
    }

def stash_changes(
    message: Optional[str] = None,
    include_untracked: bool = False,
    repo_path: str = "."
) -> Dict[str, str]:
    """
    Stash current changes.

    SECURITY: Validates commit message to prevent command injection.

    Args:
        message: Optional stash message
        include_untracked: Include untracked files
        repo_path: Repository path

    Returns:
        Dictionary with stash status

    Raises:
        GitSecurityError: If message fails validation
    """
    # Validate inputs
    try:
        from siege_utilities.git.validation import validate_commit_message, validate_repo_path
        if message:
            message = validate_commit_message(message)
        repo_path = str(validate_repo_path(repo_path))
    except ImportError:
        pass

    stash_args = ["stash"]
    if message:
        stash_args.extend(["push", "-m", message])
    if include_untracked:
        stash_args.append("-u")

    try:
        result = run_git_command(*stash_args, repo_path=repo_path)
        stash_status = "success"

        # Extract stash hash if available
        stash_hash = ""
        if "Saved working directory" in result:
            match = re.search(r'stash@{(\d+)}', result)
            if match:
                stash_hash = match.group(1)

        log_info(f"Changes stashed successfully")
        return {
            "status": stash_status,
            "stash_hash": stash_hash,
            "message": message,
            "include_untracked": include_untracked
        }
    except (RuntimeError, GitError) as e:
        stash_status = "failed"
        log_error(f"Stash failed: {e}")
        return {"status": stash_status, "error": str(e)}

def apply_stash(
    stash_ref: str = "stash@{0}",
    repo_path: str = ".",
    pop: bool = False
) -> Dict[str, str]:
    """
    Apply a stashed change.

    SECURITY: Validates stash reference to prevent command injection.

    Args:
        stash_ref: Stash reference (e.g., "stash@{0}")
        repo_path: Repository path
        pop: Pop instead of apply

    Returns:
        Dictionary with apply status

    Raises:
        GitSecurityError: If stash ref fails validation
    """
    # Validate inputs
    try:
        from siege_utilities.git.validation import has_dangerous_characters, validate_repo_path, GitSecurityError
        # Validate stash ref format
        import re
        if not re.match(r'^stash@\{\d+\}$', stash_ref):
            raise GitSecurityError(f"Invalid stash ref format: {stash_ref}")
        if has_dangerous_characters(stash_ref):
            raise GitSecurityError(f"Dangerous characters in stash ref: {stash_ref}")
        repo_path = str(validate_repo_path(repo_path))
    except ImportError:
        pass

    stash_args = ["stash", "pop" if pop else "apply", stash_ref]

    try:
        run_git_command(*stash_args, repo_path=repo_path)
        apply_status = "success"
        action = "popped" if pop else "applied"
        log_info(f"Stash {stash_ref} {action} successfully")
    except (RuntimeError, GitError) as e:
        apply_status = "failed"
        log_error(f"Stash apply failed: {e}")
        return {"status": apply_status, "error": str(e)}

    return {
        "stash_ref": stash_ref,
        "status": apply_status,
        "action": "pop" if pop else "apply"
    }

def clean_working_directory(
    repo_path: str = ".",
    force: bool = False,
    directories: bool = False
) -> Dict[str, str]:
    """Clean untracked files from working directory."""

    clean_args = ["clean"]
    if force:
        clean_args.append("-f")
    if directories:
        clean_args.append("-d")

    # First, show what would be cleaned
    dry_run_args = clean_args + ["-n"]
    dry_run_output = run_git_command(*dry_run_args, repo_path=repo_path)

    if not dry_run_output.strip():
        return {
            "status": "clean",
            "message": "Working directory is already clean"
        }

    log_info("Files to be cleaned:")
    log_info(dry_run_output)

    if not force:
        response = input("Proceed with cleaning? (y/N): ")
        if response.lower() != 'y':
            return {
                "status": "cancelled",
                "message": "Clean operation cancelled by user"
            }

    # Execute clean
    try:
        run_git_command(*clean_args, repo_path=repo_path)
        clean_status = "success"
        log_info("Working directory cleaned successfully")
    except (RuntimeError, GitError) as e:
        clean_status = "failed"
        log_error(f"Clean failed: {e}")
        return {"status": clean_status, "error": str(e)}

    return {
        "status": clean_status,
        "force": force,
        "directories": directories
    }

def reset_to_commit(
    commit_hash: str,
    reset_type: str = "soft",
    repo_path: str = "."
) -> Dict[str, str]:
    """
    Reset HEAD to a specific commit.

    SECURITY: Validates commit hash to prevent command injection.

    Args:
        commit_hash: Commit SHA to reset to
        reset_type: Type of reset (soft, mixed, hard)
        repo_path: Repository path

    Returns:
        Dictionary with reset status

    Raises:
        GitSecurityError: If commit hash fails validation
    """
    # Validate inputs
    try:
        from siege_utilities.git.validation import validate_commit_hash, validate_repo_path
        commit_hash = validate_commit_hash(commit_hash)
        repo_path = str(validate_repo_path(repo_path))
    except ImportError:
        pass

    valid_reset_types = ["soft", "mixed", "hard"]
    if reset_type not in valid_reset_types:
        raise ValueError(f"Invalid reset type. Must be one of: {valid_reset_types}")

    reset_args = ["reset", f"--{reset_type}", commit_hash]

    try:
        run_git_command(*reset_args, repo_path=repo_path)
        reset_status = "success"
        log_info(f"Reset to commit {commit_hash} ({reset_type}) successful")
    except (RuntimeError, GitError) as e:
        reset_status = "failed"
        log_error(f"Reset failed: {e}")
        return {"status": reset_status, "error": str(e)}

    return {
        "commit_hash": commit_hash,
        "reset_type": reset_type,
        "status": reset_status
    }

def cherry_pick_commit(
    commit_hash: str,
    repo_path: str = ".",
    continue_on_conflict: bool = False
) -> Dict[str, str]:
    """
    Cherry-pick a specific commit.

    SECURITY: Validates commit hash to prevent command injection.

    Args:
        commit_hash: Commit SHA to cherry-pick
        repo_path: Repository path
        continue_on_conflict: Continue after resolving conflicts

    Returns:
        Dictionary with cherry-pick status

    Raises:
        GitSecurityError: If commit hash fails validation
    """
    # Validate inputs
    try:
        from siege_utilities.git.validation import validate_commit_hash, validate_repo_path
        if not continue_on_conflict:  # Only validate if we're using the hash
            commit_hash = validate_commit_hash(commit_hash)
        repo_path = str(validate_repo_path(repo_path))
    except ImportError:
        pass

    cherry_pick_args = ["cherry-pick"]
    if continue_on_conflict:
        cherry_pick_args.append("--continue")
    else:
        cherry_pick_args.append(commit_hash)

    try:
        run_git_command(*cherry_pick_args, repo_path=repo_path)
        cherry_pick_status = "success"
        action = "continued" if continue_on_conflict else "applied"
        log_info(f"Cherry-pick {action} successfully")
    except (RuntimeError, GitError) as e:
        cherry_pick_status = "failed"
        log_error(f"Cherry-pick failed: {e}")
        return {"status": cherry_pick_status, "error": str(e)}

    return {
        "commit_hash": commit_hash,
        "status": cherry_pick_status,
        "continue_on_conflict": continue_on_conflict
    }

def create_tag(
    tag_name: str,
    message: Optional[str] = None,
    commit_hash: Optional[str] = None,
    repo_path: str = ".",
    push: bool = False
) -> Dict[str, str]:
    """
    Create a git tag.

    SECURITY: This function validates tag names to prevent command injection
    and invalid git references.

    Args:
        tag_name: Name for the tag
        message: Optional tag message
        commit_hash: Optional specific commit to tag
        repo_path: Repository path (default: current directory)
        push: Whether to push tag to remote

    Returns:
        Dictionary with tag creation status

    Raises:
        GitSecurityError: If tag name, message, or commit hash fails validation

    Example:
        >>> result = create_tag("v1.0.0", message="Release 1.0.0")
        >>>
        >>> # This will raise GitSecurityError
        >>> create_tag("<script>alert('xss')</script>")  # Invalid tag name

    Security Changes:
        - Now validates tag names against git ref name rules
        - Blocks command injection patterns
        - Validates commit hash format
        - Validates commit message content
    """
    # Import validation functions
    try:
        from siege_utilities.git.validation import (
            validate_tag_name,
            validate_commit_message,
            validate_commit_hash,
            validate_repo_path,
            GitSecurityError
        )
    except ImportError:
        # Fallback: minimal validation
        if not tag_name or not tag_name.strip():
            raise ValueError("Tag name cannot be empty")
        if any(c in tag_name for c in [';', '&', '|', '$', '`', '(', ')']):
            raise ValueError(f"Tag name contains dangerous characters: {tag_name}")
    else:
        # Validate inputs
        try:
            tag_name = validate_tag_name(tag_name)
            if message:
                message = validate_commit_message(message)
            if commit_hash:
                commit_hash = validate_commit_hash(commit_hash)
            repo_path_obj = validate_repo_path(repo_path)
            repo_path = str(repo_path_obj)
        except (GitSecurityError, ValueError) as e:
            return {"status": "failed", "error": f"Validation failed: {e}"}

    tag_args = ["tag"]
    if message:
        tag_args.extend(["-m", message])

    tag_args.append(tag_name)

    if commit_hash:
        tag_args.append(commit_hash)

    try:
        run_git_command(*tag_args, repo_path=repo_path)
        tag_status = "success"
        log_info(f"Tag {tag_name} created successfully")

        if push:
            run_git_command("push", "origin", tag_name, repo_path=repo_path)
            log_info(f"Tag {tag_name} pushed to remote")
            tag_status = "pushed"
    except (RuntimeError, GitError) as e:
        tag_status = "failed"
        log_error(f"Tag creation failed: {e}")
        return {"status": tag_status, "error": str(e)}

    return {
        "tag_name": tag_name,
        "message": message,
        "commit_hash": commit_hash,
        "status": tag_status,
        "pushed": push
    }

def push_branch(
    branch_name: Optional[str] = None,
    remote: str = "origin",
    force: bool = False,
    repo_path: str = "."
) -> Dict[str, str]:
    """
    Push a branch to remote.

    SECURITY: Validates branch and remote names to prevent command injection.

    Args:
        branch_name: Branch to push (None for current branch)
        remote: Remote repository name
        force: Force push with lease
        repo_path: Repository path

    Returns:
        Dictionary with push status

    Raises:
        GitSecurityError: If branch or remote name fails validation
    """
    # Validate inputs
    try:
        from siege_utilities.git.validation import validate_branch_name, validate_remote_name, validate_repo_path
        if branch_name:
            branch_name = validate_branch_name(branch_name)
        remote = validate_remote_name(remote)
        repo_path = str(validate_repo_path(repo_path))
    except ImportError:
        pass

    push_args = ["push"]
    if force:
        push_args.append("--force-with-lease")  # Safer than --force

    push_args.append(remote)

    if branch_name:
        push_args.append(branch_name)

    try:
        run_git_command(*push_args, repo_path=repo_path)
        push_status = "success"
        force_text = " (force)" if force else ""
        log_info(f"Branch pushed to {remote}{force_text} successfully")
    except (RuntimeError, GitError) as e:
        push_status = "failed"
        log_error(f"Push failed: {e}")
        return {"status": push_status, "error": str(e)}

    return {
        "branch_name": branch_name,
        "remote": remote,
        "force": force,
        "status": push_status
    }

def pull_branch(
    branch_name: Optional[str] = None,
    remote: str = "origin",
    rebase: bool = False,
    repo_path: str = "."
) -> Dict[str, str]:
    """
    Pull changes from remote branch.

    SECURITY: Validates branch and remote names to prevent command injection.

    Args:
        branch_name: Branch to pull (None for current branch)
        remote: Remote repository name
        rebase: Rebase instead of merge
        repo_path: Repository path

    Returns:
        Dictionary with pull status

    Raises:
        GitSecurityError: If branch or remote name fails validation
    """
    # Validate inputs
    try:
        from siege_utilities.git.validation import validate_branch_name, validate_remote_name, validate_repo_path
        if branch_name:
            branch_name = validate_branch_name(branch_name)
        remote = validate_remote_name(remote)
        repo_path = str(validate_repo_path(repo_path))
    except ImportError:
        pass

    pull_args = ["pull"]
    if rebase:
        pull_args.append("--rebase")

    pull_args.append(remote)

    if branch_name:
        pull_args.append(branch_name)

    try:
        run_git_command(*pull_args, repo_path=repo_path)
        pull_status = "success"
        rebase_text = " (rebase)" if rebase else ""
        log_info(f"Changes pulled from {remote}{rebase_text} successfully")
    except (RuntimeError, GitError) as e:
        pull_status = "failed"
        log_error(f"Pull failed: {e}")
        return {"status": pull_status, "error": str(e)}

    return {
        "branch_name": branch_name,
        "remote": remote,
        "rebase": rebase,
        "status": pull_status
    }
