"""
Hygiene utilities for maintaining siege_utilities package.
Tools for documentation, code quality, and package maintenance.
"""

from .generate_docstrings import main as generate_docstrings
from .pypi_release import (
    get_current_version,
    increment_version,
    update_version_in_setup_py,
    update_version_in_pyproject_toml,
    clean_build_artifacts,
    build_package,
    validate_package,
    upload_to_pypi,
    create_release_notes,
    full_release_workflow,
    check_release_readiness
)

__all__ = [
    'generate_docstrings',
    'get_current_version',
    'increment_version',
    'update_version_in_setup_py',
    'update_version_in_pyproject_toml',
    'clean_build_artifacts',
    'build_package',
    'validate_package',
    'upload_to_pypi',
    'create_release_notes',
    'full_release_workflow',
    'check_release_readiness'
]