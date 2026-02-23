"""
Hygiene utilities for maintaining siege_utilities package.

This module provides comprehensive tools for package maintenance including:
- Documentation generation and management
- PyPI release automation and version management
- Build artifact cleanup and validation
- Package publishing workflows

Key Features:
- Automatic docstring generation for undocumented functions
- Complete PyPI release workflow with version management
- Package building, validation, and upload automation
- Release notes generation and readiness checking
- Support for both setup.py and pyproject.toml formats

For detailed usage examples and API documentation, see:
- siege_utilities.hygiene.README.md
- siege_utilities.hygiene.pypi_release module

Example Usage:
    # Generate docstrings
    from siege_utilities.hygiene import generate_docstrings
    generate_docstrings()
    
    # Check release readiness
    from siege_utilities.hygiene import check_release_readiness
    is_ready, issues = check_release_readiness()
    
    # Full release workflow
    from siege_utilities.hygiene import full_release_workflow
    success, message = full_release_workflow(
        increment_type="patch",
        changes=["Fixed bug", "Added feature"],
        dry_run=True
    )
"""

from .generate_docstrings import main as generate_docstrings
# DEPRECATED: pypi_release functions are deprecated as of v2.0.0.
# Use scripts/release_manager.py instead. These re-exports are kept
# for backward compatibility and will be removed in v3.0.0.
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