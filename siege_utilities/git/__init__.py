"""
Git utilities for siege_utilities package.
Comprehensive git operations, branch management, and status reporting.
"""

from .branch_analyzer import (
    analyze_branch_status, 
    generate_branch_report,
    get_commit_history,
    categorize_commits,
    get_file_changes
)

from .git_operations import (
    create_feature_branch,
    switch_branch,
    merge_branch,
    rebase_branch,
    stash_changes,
    apply_stash,
    clean_working_directory,
    reset_to_commit,
    cherry_pick_commit,
    create_tag,
    push_branch,
    pull_branch
)

from .git_status import (
    get_repository_status,
    get_branch_info,
    get_remote_info,
    get_stash_list,
    get_tag_list,
    get_log_summary
)

from .git_workflow import (
    start_feature_workflow,
    complete_feature_workflow,
    hotfix_workflow,
    release_workflow,
    validate_branch_naming,
    enforce_commit_conventions
)

__all__ = [
    # Branch Analysis
    'analyze_branch_status',
    'generate_branch_report', 
    'get_commit_history',
    'categorize_commits',
    'get_file_changes',
    
    # Git Operations
    'create_feature_branch',
    'switch_branch',
    'merge_branch',
    'rebase_branch',
    'stash_changes',
    'apply_stash',
    'clean_working_directory',
    'reset_to_commit',
    'cherry_pick_commit',
    'create_tag',
    'push_branch',
    'pull_branch',
    
    # Git Status
    'get_repository_status',
    'get_branch_info',
    'get_remote_info',
    'get_stash_list',
    'get_tag_list',
    'get_log_summary',
    
    # Git Workflow
    'start_feature_workflow',
    'complete_feature_workflow',
    'hotfix_workflow',
    'release_workflow',
    'validate_branch_naming',
    'enforce_commit_conventions'
]
