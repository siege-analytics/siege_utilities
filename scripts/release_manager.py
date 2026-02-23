#!/usr/bin/env python3
"""
Release Manager for Siege Utilities

Updates version across all four locations (pyproject.toml, setup.py, __init__.py x2),
runs tests, builds the package, validates with twine, uploads to PyPI,
and optionally creates GitHub releases.

Usage:
    python scripts/release_manager.py --check          # Check version consistency
    python scripts/release_manager.py --bump patch     # Bump patch version
    python scripts/release_manager.py --build          # Build package
    python scripts/release_manager.py --build --clean  # Clean + build
    python scripts/release_manager.py --release --bump-type minor --release-notes "..."
    python scripts/release_manager.py --release --bump-type major --changelog --pypi
    python scripts/release_manager.py --release --bump-type patch --dry-run
"""

import os
import sys
import subprocess
import shutil
import json
import re
import logging
import glob as globmod
from pathlib import Path
from typing import Dict, List, Optional
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


def clean_build_artifacts() -> bool:
    """Remove dist/, build/, and *.egg-info directories."""
    logger.info("Cleaning build artifacts...")
    cleaned = []
    for dirname in ['dist', 'build']:
        target = PROJECT_ROOT / dirname
        if target.exists():
            shutil.rmtree(target)
            cleaned.append(str(dirname))

    for egg_info in PROJECT_ROOT.glob('*.egg-info'):
        shutil.rmtree(egg_info)
        cleaned.append(egg_info.name)

    for egg_info in (PROJECT_ROOT / 'siege_utilities').glob('*.egg-info'):
        shutil.rmtree(egg_info)
        cleaned.append(egg_info.name)

    if cleaned:
        logger.info(f"Cleaned: {', '.join(cleaned)}")
    else:
        logger.info("No build artifacts to clean")
    return True


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


def validate_build() -> bool:
    """Validate built distributions with twine check."""
    dist_dir = PROJECT_ROOT / 'dist'
    dist_files = list(dist_dir.glob('*')) if dist_dir.exists() else []
    if not dist_files:
        logger.error("No distribution files found in dist/")
        return False

    logger.info("Validating package with twine...")
    result = subprocess.run(
        [sys.executable, '-m', 'twine', 'check'] + [str(f) for f in dist_files],
        cwd=PROJECT_ROOT,
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        logger.info("Package validation passed")
        return True
    logger.error(f"Package validation failed:\n{result.stdout}\n{result.stderr}")
    return False


def upload_to_pypi(repository: str = 'pypi', token: Optional[str] = None,
                   dry_run: bool = False) -> bool:
    """Upload distributions to PyPI using twine.

    Args:
        repository: 'pypi' or 'testpypi'
        token: PyPI API token. Falls back to PYPI_API_TOKEN env var.
        dry_run: If True, log what would happen but don't upload.
    """
    resolved_token = token or os.environ.get('PYPI_API_TOKEN')
    if not resolved_token:
        logger.error("No PyPI token provided (use --token or PYPI_API_TOKEN env var)")
        return False

    dist_dir = PROJECT_ROOT / 'dist'
    dist_files = list(dist_dir.glob('*')) if dist_dir.exists() else []
    if not dist_files:
        logger.error("No distribution files found in dist/")
        return False

    if dry_run:
        logger.info(f"[DRY RUN] Would upload {len(dist_files)} file(s) to {repository}")
        return True

    cmd = [sys.executable, '-m', 'twine', 'upload',
           '--username', '__token__', '--password', resolved_token]
    if repository == 'testpypi':
        cmd.extend(['--repository', 'testpypi'])
    cmd.extend([str(f) for f in dist_files])

    logger.info(f"Uploading to {repository}...")
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    if result.returncode == 0:
        logger.info(f"Upload to {repository} succeeded")
        return True
    logger.error(f"Upload to {repository} failed")
    return False


def git_commit_and_tag(version: str, message: Optional[str] = None,
                       dry_run: bool = False) -> bool:
    """Commit version file changes, create annotated tag, push both.

    Args:
        version: Version string (tag will be vX.Y.Z)
        message: Tag annotation message. Defaults to 'Release vX.Y.Z'.
        dry_run: If True, log what would happen but don't execute.
    """
    tag = f"v{version}"
    msg = message or f"Release {tag}"

    version_paths = [str(spec['path'].relative_to(PROJECT_ROOT))
                     for spec in VERSION_FILES.values()]

    changelog = PROJECT_ROOT / 'CHANGELOG.md'
    if changelog.exists():
        version_paths.append('CHANGELOG.md')

    if dry_run:
        logger.info(f"[DRY RUN] Would commit {version_paths}, tag {tag}, push")
        return True

    try:
        subprocess.run(['git', 'add'] + version_paths,
                       cwd=PROJECT_ROOT, check=True)
        subprocess.run(['git', 'commit', '-m', f"chore: release {tag}"],
                       cwd=PROJECT_ROOT, check=True)
        subprocess.run(['git', 'tag', '-a', tag, '-m', msg],
                       cwd=PROJECT_ROOT, check=True)
        subprocess.run(['git', 'push'], cwd=PROJECT_ROOT, check=True)
        subprocess.run(['git', 'push', '--tags'], cwd=PROJECT_ROOT, check=True)
        logger.info(f"Committed, tagged {tag}, and pushed")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Git operation failed: {e}")
        return False


def extract_changelog_notes(version: str) -> Optional[str]:
    """Parse CHANGELOG.md and return the section for a given version.

    Looks for a heading like ``## [X.Y.Z]`` or ``## [Unreleased]`` and
    returns all content until the next ``## `` heading.
    """
    changelog = PROJECT_ROOT / 'CHANGELOG.md'
    if not changelog.exists():
        logger.warning("CHANGELOG.md not found")
        return None

    content = changelog.read_text()
    # Match ## [version] or ## [Unreleased]
    pattern = rf'^## \[{re.escape(version)}\].*$'
    match = re.search(pattern, content, re.MULTILINE)
    if not match:
        # Also try "Unreleased" if version not found explicitly
        if version.lower() == 'unreleased':
            match = re.search(r'^## \[Unreleased\].*$', content, re.MULTILINE)
        if not match:
            logger.warning(f"No changelog section found for {version}")
            return None

    start = match.end()
    # Find the next ## heading
    next_heading = re.search(r'^## \[', content[start:], re.MULTILINE)
    if next_heading:
        section = content[start:start + next_heading.start()]
    else:
        section = content[start:]

    return section.strip()


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


def create_github_release(version: str, notes: str, dry_run: bool = False) -> bool:
    """Create a GitHub release using gh CLI."""
    if dry_run:
        logger.info(f"[DRY RUN] Would create GitHub release v{version}")
        return True

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
    parser.add_argument('--changelog', action='store_true',
                        help='Use CHANGELOG.md for release notes (instead of --release-notes)')
    parser.add_argument('--skip-tests', action='store_true', help='Skip tests during release')
    parser.add_argument('--skip-github', action='store_true', help='Skip GitHub release creation')
    parser.add_argument('--pypi', action='store_true', help='Upload to PyPI after build')
    parser.add_argument('--repository', choices=['pypi', 'testpypi'], default='pypi',
                        help='PyPI repository target (default: pypi)')
    parser.add_argument('--token', type=str,
                        help='PyPI API token (or set PYPI_API_TOKEN env var)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show actions without executing side effects')
    parser.add_argument('--clean', action='store_true',
                        help='Clean build artifacts before building')

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
        if args.clean:
            clean_build_artifacts()
        if not build_package():
            sys.exit(1)
        if not validate_build():
            sys.exit(1)
        if args.pypi:
            if not upload_to_pypi(args.repository, args.token, args.dry_run):
                sys.exit(1)

    elif args.test:
        sys.exit(0 if run_tests() else 1)

    elif args.verify:
        sys.exit(0 if verify_import() else 1)

    elif args.release:
        if not args.bump_type:
            parser.error("--release requires --bump-type")
        if not args.release_notes and not args.changelog:
            parser.error("--release requires --release-notes or --changelog")

        # 1. Check consistency
        logger.info("Step 1/10: Checking version consistency...")
        status = check_consistency()
        if not status['consistent']:
            logger.error(f"Version inconsistency: {status['versions']}")
            sys.exit(1)

        # 2. Tests
        logger.info("Step 2/10: Running tests...")
        if not args.skip_tests:
            if not run_tests():
                logger.error("Tests failed, aborting release")
                sys.exit(1)
        else:
            logger.info("Tests skipped (--skip-tests)")

        # 3. Bump
        logger.info("Step 3/10: Bumping version...")
        if args.dry_run:
            current = get_current_version()
            parts = current.split('.')
            major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
            if args.bump_type == 'major':
                new_ver = f"{major + 1}.0.0"
            elif args.bump_type == 'minor':
                new_ver = f"{major}.{minor + 1}.0"
            else:
                new_ver = f"{major}.{minor}.{patch + 1}"
            logger.info(f"[DRY RUN] Would bump {current} -> {new_ver}")
        else:
            new_ver = bump_version(args.bump_type)
            logger.info(f"Version bumped to {new_ver}")

        # 4. Verify import
        logger.info("Step 4/10: Verifying import...")
        if not args.dry_run:
            if not verify_import():
                logger.error("Import verification failed")
                sys.exit(1)
        else:
            logger.info("[DRY RUN] Would verify import")

        # 5. Clean build artifacts
        logger.info("Step 5/10: Cleaning build artifacts...")
        clean_build_artifacts()

        # 6. Build
        logger.info("Step 6/10: Building package...")
        if not args.dry_run:
            if not build_package():
                sys.exit(1)
        else:
            logger.info("[DRY RUN] Would build package")

        # 7. Validate
        logger.info("Step 7/10: Validating package...")
        if not args.dry_run:
            if not validate_build():
                sys.exit(1)
        else:
            logger.info("[DRY RUN] Would validate package")

        # 8. Upload to PyPI
        logger.info("Step 8/10: PyPI upload...")
        if args.pypi:
            if not upload_to_pypi(args.repository, args.token, args.dry_run):
                sys.exit(1)
        else:
            logger.info("PyPI upload skipped (use --pypi to enable)")

        # 9. Git commit + tag + push
        logger.info("Step 9/10: Git commit and tag...")
        # Resolve release notes
        if args.changelog:
            notes = extract_changelog_notes(new_ver) or extract_changelog_notes('Unreleased')
            if not notes:
                logger.warning("Could not extract changelog notes, using bump type as fallback")
                notes = f"Release v{new_ver}"
        else:
            notes = args.release_notes

        if not git_commit_and_tag(new_ver, notes, args.dry_run):
            logger.warning("Git commit/tag failed (non-fatal)")

        # 10. GitHub release
        logger.info("Step 10/10: GitHub release...")
        if not args.skip_github:
            if not create_github_release(new_ver, notes, args.dry_run):
                logger.warning("GitHub release creation failed (non-fatal)")
        else:
            logger.info("GitHub release skipped (--skip-github)")

        logger.info(f"Release {new_ver} complete" +
                     (" (dry run)" if args.dry_run else ""))

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
