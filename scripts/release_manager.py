#!/usr/bin/env python3
"""
Release Manager for Siege Utilities

Updates version across all three locations (pyproject.toml, setup.py, __init__.py),
runs tests, builds the package, and optionally creates GitHub releases.

Usage:
    python scripts/release_manager.py --check          # Check version consistency
    python scripts/release_manager.py --bump patch     # Bump patch version
    python scripts/release_manager.py --build          # Build package
    python scripts/release_manager.py --release --bump-type minor --release-notes "..."
"""

import os
import sys
import subprocess
import json
import re
import logging
from pathlib import Path
from typing import Dict, Optional
import argparse
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Resolve project root (parent of scripts/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

VERSION_FILES = {
    'pyproject.toml': {
        'path': PROJECT_ROOT / 'pyproject.toml',
        'pattern': r'(version\s*=\s*")[^"]+(")',
    },
    'setup.py': {
        'path': PROJECT_ROOT / 'setup.py',
        'pattern': r'(version\s*=\s*")[^"]+(")',
    },
    '__init__.py __version__': {
        'path': PROJECT_ROOT / 'siege_utilities' / '__init__.py',
        'pattern': r'(__version__\s*=\s*")[^"]+(")',
    },
    '__init__.py get_package_info': {
        'path': PROJECT_ROOT / 'siege_utilities' / '__init__.py',
        'pattern': r"('version':\s*')[^']+(')",
    },
}


def read_versions() -> Dict[str, str]:
    """Read current version from each location."""
    versions = {}
    for name, spec in VERSION_FILES.items():
        content = spec['path'].read_text()
        match = re.search(spec['pattern'], content)
        if match:
            # The version is between the two capture groups
            full_match = re.search(spec['pattern'].replace(r'[^"]+', r'([^"]+)').replace(r"[^']+", r"([^']+)"), content)
            if full_match:
                versions[name] = full_match.group(2) if full_match.lastindex >= 2 else full_match.group(1)
        else:
            versions[name] = 'NOT FOUND'
    return versions


def get_current_version() -> str:
    """Get canonical version from pyproject.toml."""
    content = (PROJECT_ROOT / 'pyproject.toml').read_text()
    match = re.search(r'version\s*=\s*"([^"]+)"', content)
    if match:
        return match.group(1)
    raise ValueError("Could not find version in pyproject.toml")


def check_consistency() -> Dict:
    """Check version consistency across all files."""
    versions = read_versions()
    unique = set(versions.values()) - {'NOT FOUND'}
    return {
        'versions': versions,
        'consistent': len(unique) <= 1,
        'canonical': get_current_version(),
    }


def set_version(new_version: str):
    """Set version across all files."""
    for name, spec in VERSION_FILES.items():
        path = spec['path']
        content = path.read_text()
        new_content = re.sub(spec['pattern'], rf'\g<1>{new_version}\2', content)
        if new_content == content:
            logger.warning(f"No replacement made in {name}")
        else:
            path.write_text(new_content)
            logger.info(f"Updated {name} -> {new_version}")


def bump_version(bump_type: str) -> str:
    """Bump version and return new version string."""
    current = get_current_version()
    parts = current.split('.')
    if len(parts) != 3:
        raise ValueError(f"Unexpected version format: {current}")

    major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])

    if bump_type == 'major':
        major += 1; minor = 0; patch = 0
    elif bump_type == 'minor':
        minor += 1; patch = 0
    elif bump_type == 'patch':
        patch += 1
    else:
        raise ValueError(f"Invalid bump type: {bump_type}")

    new_version = f"{major}.{minor}.{patch}"
    set_version(new_version)
    return new_version


def run_tests() -> bool:
    """Run the test suite."""
    logger.info("Running tests...")
    result = subprocess.run(
        [sys.executable, '-m', 'pytest', 'tests/', '-x', '-q'],
        cwd=PROJECT_ROOT,
    )
    return result.returncode == 0


def build_package() -> bool:
    """Build sdist and wheel using python -m build."""
    logger.info("Building package...")
    result = subprocess.run(
        [sys.executable, '-m', 'build'],
        cwd=PROJECT_ROOT,
    )
    if result.returncode == 0:
        logger.info("Package built successfully")
        return True
    logger.error("Package build failed")
    return False


def verify_import() -> bool:
    """Verify the package imports and reports the correct version."""
    result = subprocess.run(
        [sys.executable, '-c',
         'import siege_utilities; print(siege_utilities.__version__)'],
        cwd=PROJECT_ROOT,
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        logger.error(f"Import failed: {result.stderr}")
        return False
    reported = result.stdout.strip().split('\n')[-1]
    expected = get_current_version()
    if reported != expected:
        logger.error(f"Version mismatch: import says {reported}, pyproject says {expected}")
        return False
    logger.info(f"Import OK, version {reported}")
    return True


def create_github_release(version: str, notes: str) -> bool:
    """Create a GitHub release using gh CLI."""
    result = subprocess.run(
        ['gh', 'release', 'create', f'v{version}',
         '--repo', 'siege-analytics/siege_utilities',
         '--title', f'v{version}',
         '--notes', notes],
        cwd=PROJECT_ROOT,
    )
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="Release Manager for Siege Utilities")
    parser.add_argument('--check', action='store_true', help='Check version consistency')
    parser.add_argument('--bump', choices=['major', 'minor', 'patch'], help='Bump version')
    parser.add_argument('--set-version', type=str, help='Set explicit version')
    parser.add_argument('--build', action='store_true', help='Build package')
    parser.add_argument('--test', action='store_true', help='Run tests')
    parser.add_argument('--verify', action='store_true', help='Verify import + version')
    parser.add_argument('--release', action='store_true', help='Full release workflow')
    parser.add_argument('--bump-type', choices=['major', 'minor', 'patch'],
                        help='Bump type for --release')
    parser.add_argument('--release-notes', type=str, help='Release notes for --release')
    parser.add_argument('--skip-tests', action='store_true', help='Skip tests during release')
    parser.add_argument('--skip-github', action='store_true', help='Skip GitHub release creation')

    args = parser.parse_args()

    if args.check:
        status = check_consistency()
        print(json.dumps(status, indent=2))
        sys.exit(0 if status['consistent'] else 1)

    elif args.bump:
        new_ver = bump_version(args.bump)
        print(f"Bumped to {new_ver}")

    elif args.set_version:
        set_version(args.set_version)
        print(f"Set version to {args.set_version}")

    elif args.build:
        sys.exit(0 if build_package() else 1)

    elif args.test:
        sys.exit(0 if run_tests() else 1)

    elif args.verify:
        sys.exit(0 if verify_import() else 1)

    elif args.release:
        if not args.bump_type or not args.release_notes:
            parser.error("--release requires --bump-type and --release-notes")

        # 1. Check consistency
        status = check_consistency()
        if not status['consistent']:
            logger.error(f"Version inconsistency: {status['versions']}")
            sys.exit(1)

        # 2. Tests
        if not args.skip_tests:
            if not run_tests():
                logger.error("Tests failed, aborting release")
                sys.exit(1)

        # 3. Bump
        new_ver = bump_version(args.bump_type)
        logger.info(f"Version bumped to {new_ver}")

        # 4. Verify import
        if not verify_import():
            logger.error("Import verification failed")
            sys.exit(1)

        # 5. Build
        if not build_package():
            sys.exit(1)

        # 6. GitHub release
        if not args.skip_github:
            if not create_github_release(new_ver, args.release_notes):
                logger.warning("GitHub release creation failed (non-fatal)")

        logger.info(f"Release {new_ver} complete")

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
