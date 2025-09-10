"""
PyPI Release Management for siege_utilities package.

This module provides comprehensive functions for releasing packages to PyPI,
including version management, build validation, and automated release workflows.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json
import re
from datetime import datetime


def get_current_version(setup_py_path: str = "setup.py") -> str:
    """
    Extract current version from setup.py.
    
    Args:
        setup_py_path: Path to setup.py file
        
    Returns:
        str: Current version string
        
    Raises:
        FileNotFoundError: If setup.py doesn't exist
        ValueError: If version cannot be extracted
    """
    try:
        with open(setup_py_path, 'r') as f:
            content = f.read()
        
        # Look for version in setup() call
        version_match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
        if version_match:
            return version_match.group(1)
        
        # Look for version in __version__ variable
        version_match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
        if version_match:
            return version_match.group(1)
        
        raise ValueError("Version not found in setup.py")
        
    except FileNotFoundError:
        raise FileNotFoundError(f"setup.py not found at {setup_py_path}")


def increment_version(version: str, increment_type: str = "patch") -> str:
    """
    Increment version number.
    
    Args:
        version: Current version string (e.g., "1.2.3")
        increment_type: Type of increment ("major", "minor", "patch")
        
    Returns:
        str: New version string
        
    Raises:
        ValueError: If version format is invalid or increment_type is unknown
    """
    try:
        parts = version.split('.')
        if len(parts) != 3:
            raise ValueError("Version must be in format 'major.minor.patch'")
        
        major, minor, patch = map(int, parts)
        
        if increment_type == "major":
            return f"{major + 1}.0.0"
        elif increment_type == "minor":
            return f"{major}.{minor + 1}.0"
        elif increment_type == "patch":
            return f"{major}.{minor}.{patch + 1}"
        else:
            raise ValueError("increment_type must be 'major', 'minor', or 'patch'")
            
    except ValueError as e:
        raise ValueError(f"Invalid version format or increment type: {e}")


def update_version_in_setup_py(setup_py_path: str, new_version: str) -> bool:
    """
    Update version in setup.py file.
    
    Args:
        setup_py_path: Path to setup.py file
        new_version: New version string
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with open(setup_py_path, 'r') as f:
            content = f.read()
        
        # Replace version in setup() call
        content = re.sub(
            r'version\s*=\s*["\'][^"\']+["\']',
            f'version="{new_version}"',
            content
        )
        
        # Replace version in __version__ variable if it exists
        content = re.sub(
            r'__version__\s*=\s*["\'][^"\']+["\']',
            f'__version__="{new_version}"',
            content
        )
        
        with open(setup_py_path, 'w') as f:
            f.write(content)
        
        return True
        
    except Exception as e:
        print(f"Error updating version in setup.py: {e}")
        return False


def update_version_in_pyproject_toml(pyproject_toml_path: str, new_version: str) -> bool:
    """
    Update version in pyproject.toml file.
    
    Args:
        pyproject_toml_path: Path to pyproject.toml file
        new_version: New version string
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with open(pyproject_toml_path, 'r') as f:
            content = f.read()
        
        # Replace version in [project] section
        content = re.sub(
            r'version\s*=\s*["\'][^"\']+["\']',
            f'version = "{new_version}"',
            content
        )
        
        with open(pyproject_toml_path, 'w') as f:
            f.write(content)
        
        return True
        
    except Exception as e:
        print(f"Error updating version in pyproject.toml: {e}")
        return False


def clean_build_artifacts() -> bool:
    """
    Clean build artifacts and temporary files.
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Directories to clean
        dirs_to_clean = ['build', 'dist', '*.egg-info', '__pycache__']
        
        for pattern in dirs_to_clean:
            for path in Path('.').glob(pattern):
                if path.is_dir():
                    shutil.rmtree(path)
                    print(f"Removed directory: {path}")
        
        # Files to clean
        files_to_clean = ['*.pyc', '*.pyo', '*.pyd']
        
        for pattern in files_to_clean:
            for path in Path('.').glob(pattern):
                if path.is_file():
                    path.unlink()
                    print(f"Removed file: {path}")
        
        return True
        
    except Exception as e:
        print(f"Error cleaning build artifacts: {e}")
        return False


def build_package() -> Tuple[bool, str]:
    """
    Build the package for distribution.
    
    Returns:
        Tuple[bool, str]: (success, output_message)
    """
    try:
        # Clean first
        clean_build_artifacts()
        
        # Build using setuptools
        result = subprocess.run(
            [sys.executable, 'setup.py', 'sdist', 'bdist_wheel'],
            capture_output=True,
            text=True,
            cwd=Path.cwd()
        )
        
        if result.returncode == 0:
            return True, "Package built successfully"
        else:
            return False, f"Build failed: {result.stderr}"
            
    except Exception as e:
        return False, f"Build error: {e}"


def validate_package() -> Tuple[bool, List[str]]:
    """
    Validate the built package.
    
    Returns:
        Tuple[bool, List[str]]: (is_valid, list_of_issues)
    """
    issues = []
    
    try:
        # Check if dist directory exists
        dist_dir = Path('dist')
        if not dist_dir.exists():
            issues.append("dist directory not found - package not built")
            return False, issues
        
        # Check for source distribution
        sdist_files = list(dist_dir.glob('*.tar.gz'))
        if not sdist_files:
            issues.append("Source distribution (.tar.gz) not found")
        
        # Check for wheel distribution
        wheel_files = list(dist_dir.glob('*.whl'))
        if not wheel_files:
            issues.append("Wheel distribution (.whl) not found")
        
        # Validate wheel using twine
        if wheel_files:
            try:
                result = subprocess.run(
                    ['twine', 'check', str(wheel_files[0])],
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    issues.append(f"Wheel validation failed: {result.stderr}")
            except FileNotFoundError:
                issues.append("twine not installed - cannot validate wheel")
        
        return len(issues) == 0, issues
        
    except Exception as e:
        issues.append(f"Validation error: {e}")
        return False, issues


def upload_to_pypi(
    repository: str = "pypi",
    username: Optional[str] = None,
    password: Optional[str] = None,
    token: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Upload package to PyPI.
    
    Args:
        repository: Repository to upload to ("pypi" or "testpypi")
        username: PyPI username (if not using token)
        password: PyPI password (if not using token)
        token: PyPI API token (preferred)
        
    Returns:
        Tuple[bool, str]: (success, output_message)
    """
    try:
        # Check if dist directory exists
        dist_dir = Path('dist')
        if not dist_dir.exists():
            return False, "dist directory not found - build package first"
        
        # Build twine command
        cmd = ['twine', 'upload']
        
        if repository == "testpypi":
            cmd.extend(['--repository', 'testpypi'])
        
        if token:
            cmd.extend(['--username', '__token__', '--password', token])
        elif username and password:
            cmd.extend(['--username', username, '--password', password])
        else:
            return False, "Must provide either token or username/password"
        
        # Add all distribution files
        cmd.extend(['dist/*'])
        
        # Upload
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            return True, "Package uploaded successfully"
        else:
            return False, f"Upload failed: {result.stderr}"
            
    except Exception as e:
        return False, f"Upload error: {e}"


def create_release_notes(version: str, changes: List[str]) -> str:
    """
    Create release notes for the version.
    
    Args:
        version: Version string
        changes: List of changes/features
        
    Returns:
        str: Formatted release notes
    """
    notes = f"# Siege Utilities v{version}\n\n"
    notes += f"Released on {datetime.now().strftime('%Y-%m-%d')}\n\n"
    
    if changes:
        notes += "## Changes\n\n"
        for change in changes:
            notes += f"- {change}\n"
        notes += "\n"
    
    notes += "## Installation\n\n"
    notes += "```bash\n"
    notes += f"pip install siege-utilities=={version}\n"
    notes += "```\n\n"
    
    notes += "## Full Installation with Extras\n\n"
    notes += "```bash\n"
    notes += f"pip install siege-utilities[{version}][geo,distributed,analytics,reporting,streamlit,export,performance,dev]\n"
    notes += "```\n"
    
    return notes


def full_release_workflow(
    increment_type: str = "patch",
    changes: Optional[List[str]] = None,
    repository: str = "pypi",
    token: Optional[str] = None,
    dry_run: bool = False
) -> Tuple[bool, str]:
    """
    Execute full release workflow.
    
    Args:
        increment_type: Type of version increment ("major", "minor", "patch")
        changes: List of changes for release notes
        repository: Repository to upload to ("pypi" or "testpypi")
        token: PyPI API token
        dry_run: If True, don't actually upload
        
    Returns:
        Tuple[bool, str]: (success, output_message)
    """
    try:
        print("🚀 Starting full release workflow...")
        
        # 1. Get current version
        current_version = get_current_version()
        print(f"📋 Current version: {current_version}")
        
        # 2. Calculate new version
        new_version = increment_version(current_version, increment_type)
        print(f"📈 New version: {new_version}")
        
        # 3. Update version in files
        print("📝 Updating version in files...")
        setup_updated = update_version_in_setup_py("setup.py", new_version)
        pyproject_updated = update_version_in_pyproject_toml("pyproject.toml", new_version)
        
        if not setup_updated:
            return False, "Failed to update version in setup.py"
        
        # 4. Build package
        print("🔨 Building package...")
        build_success, build_message = build_package()
        if not build_success:
            return False, f"Build failed: {build_message}"
        
        # 5. Validate package
        print("✅ Validating package...")
        is_valid, issues = validate_package()
        if not is_valid:
            return False, f"Package validation failed: {issues}"
        
        # 6. Upload to PyPI (if not dry run)
        if not dry_run:
            print("📤 Uploading to PyPI...")
            upload_success, upload_message = upload_to_pypi(repository, token=token)
            if not upload_success:
                return False, f"Upload failed: {upload_message}"
        else:
            print("🔍 Dry run - skipping upload")
        
        # 7. Create release notes
        if changes:
            release_notes = create_release_notes(new_version, changes)
            with open(f"RELEASE_NOTES_v{new_version}.md", 'w') as f:
                f.write(release_notes)
            print(f"📄 Release notes created: RELEASE_NOTES_v{new_version}.md")
        
        success_message = f"✅ Release workflow completed successfully! Version {new_version}"
        if dry_run:
            success_message += " (dry run)"
        
        return True, success_message
        
    except Exception as e:
        return False, f"Release workflow failed: {e}"


def check_release_readiness() -> Tuple[bool, List[str]]:
    """
    Check if the package is ready for release.
    
    Returns:
        Tuple[bool, List[str]]: (is_ready, list_of_issues)
    """
    issues = []
    
    try:
        # Check if setup.py exists
        if not Path("setup.py").exists():
            issues.append("setup.py not found")
        
        # Check if pyproject.toml exists
        if not Path("pyproject.toml").exists():
            issues.append("pyproject.toml not found")
        
        # Check if README.md exists
        if not Path("README.md").exists():
            issues.append("README.md not found")
        
        # Check if tests exist
        if not Path("tests").exists():
            issues.append("tests directory not found")
        
        # Check if version is valid
        try:
            version = get_current_version()
            if not re.match(r'^\d+\.\d+\.\d+$', version):
                issues.append(f"Invalid version format: {version}")
        except Exception as e:
            issues.append(f"Version check failed: {e}")
        
        # Check if package can be imported
        try:
            import siege_utilities
            if not hasattr(siege_utilities, '__version__'):
                issues.append("Package missing __version__ attribute")
        except ImportError as e:
            issues.append(f"Package import failed: {e}")
        
        return len(issues) == 0, issues
        
    except Exception as e:
        issues.append(f"Readiness check failed: {e}")
        return False, issues


if __name__ == "__main__":
    # Example usage
    print("PyPI Release Management for siege_utilities")
    print("=" * 50)
    
    # Check release readiness
    is_ready, issues = check_release_readiness()
    if is_ready:
        print("✅ Package is ready for release!")
    else:
        print("❌ Package is not ready for release:")
        for issue in issues:
            print(f"  - {issue}")
    
    # Show current version
    try:
        version = get_current_version()
        print(f"📋 Current version: {version}")
    except Exception as e:
        print(f"❌ Could not get version: {e}")
