#!/usr/bin/env python3
"""
Release Manager for Siege Utilities

Updates version across all five locations (pyproject.toml, setup.py, __init__.py, docs/conf.py x2),
runs tests, builds the package, validates with twine, merges develop → main (gitflow),
tags the release, uploads to PyPI, and creates GitHub releases.

Usage:
    python scripts/release_manager.py --check          # Check version consistency
    python scripts/release_manager.py --bump patch     # Bump patch version
    python scripts/release_manager.py --build          # Build package
    python scripts/release_manager.py --build --clean  # Clean + build
    python scripts/release_manager.py --release --bump-type minor --release-notes "..."
    python scripts/release_manager.py --release --bump-type major --changelog
    python scripts/release_manager.py --release --target-version 3.1.0 --changelog
    python scripts/release_manager.py --release --bump-type patch --dry-run

Release workflow (12 steps):
    1. Check version consistency
    2. Run tests (unless --skip-tests)
    3. Bump or set version
    4. Verify import
    5. Clean build artifacts
    6. Build sdist + wheel
    7. Validate with twine
    8. Resolve release notes
    9. Merge develop → main (gitflow)
   10. Tag on main + push
   11. Upload to PyPI (always — requires PYPI_API_TOKEN or --token)
   12. Create GitHub release (unless --skip-github)
"""

import os
import sys
import subprocess
import shutil
import json
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional
import argparse

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
    'docs/conf.py': {
        'path': PROJECT_ROOT / 'docs' / 'conf.py',
        'pattern': r"(release\s*=\s*')[^']+(')",
    },
    'docs/source/conf.py': {
        'path': PROJECT_ROOT / 'docs' / 'source' / 'conf.py',
        'pattern': r"(release\s*=\s*')[^']+(')",
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


def check_ci_status() -> bool:
    """Check that the latest CI run on the current branch passed.

    Returns True if all required jobs succeeded, False otherwise.
    Requires `gh` CLI to be authenticated.
    """
    try:
        branch = subprocess.run(
            ['git', 'branch', '--show-current'],
            capture_output=True, text=True, check=True,
            cwd=PROJECT_ROOT,
        ).stdout.strip()

        result = subprocess.run(
            ['gh', 'run', 'list', '--branch', branch, '--limit', '20', '--json',
             'conclusion,status,name,workflowName,createdAt'],
            capture_output=True, text=True, check=True,
            cwd=PROJECT_ROOT,
        )
        runs = json.loads(result.stdout)
        if not runs:
            logger.warning(f"No CI runs found for branch {branch}")
            return False

        workflow_runs = [
            r for r in runs
            if r.get('workflowName') == 'Siege Utilities CI/CD'
        ]
        if not workflow_runs:
            logger.warning(
                f"No 'Siege Utilities CI/CD' runs found for branch {branch}"
            )
            return False

        run = workflow_runs[0]
        if run.get('status') != 'completed':
            logger.warning(f"Latest CI run is {run.get('status')}, not completed")
            return False

        if run.get('conclusion') != 'success':
            logger.warning(f"Latest CI run conclusion: {run.get('conclusion')}")
            return False

        logger.info(f"CI check passed: {run.get('name')} on {branch}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logger.warning(f"Could not check CI status: {e}")
        return False


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


def validate_target_version(target: str) -> str:
    """Validate an explicit target version string.

    Checks:
      1. Format is X.Y.Z (three non-negative integers)
      2. Target is greater than or equal to the current version

    If the target equals the current version, the version is already bumped
    and the release proceeds without a version change (merge + tag + publish).

    Returns the validated version string, or raises ValueError.
    """
    parts = target.split('.')
    if len(parts) != 3:
        raise ValueError(f"Version must be X.Y.Z format, got: {target}")

    try:
        target_tuple = tuple(int(p) for p in parts)
    except ValueError:
        raise ValueError(f"Version components must be integers, got: {target}")

    if any(p < 0 for p in target_tuple):
        raise ValueError(f"Version components must be non-negative, got: {target}")

    current = get_current_version()
    current_tuple = tuple(int(p) for p in current.split('.'))

    if target_tuple < current_tuple:
        raise ValueError(
            f"Target version {target} must be >= current version {current}"
        )

    if target_tuple == current_tuple:
        logger.info(f"Target version {target} matches current — version already bumped")
    else:
        logger.info(f"Target version {target} validated (current: {current})")
    return target


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


def _git(args: List[str], check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    """Run a git command in the project root."""
    return subprocess.run(
        ['git'] + args,
        cwd=PROJECT_ROOT,
        check=check,
        capture_output=capture,
        text=True,
    )


def _current_branch() -> str:
    """Return the name of the current git branch."""
    return _git(['branch', '--show-current'], capture=True).stdout.strip()


def _branch_exists(branch: str) -> bool:
    """Check whether a local branch exists."""
    result = _git(['rev-parse', '--verify', branch], check=False, capture=True)
    return result.returncode == 0


def _is_clean() -> bool:
    """Return True when the working tree has no uncommitted changes."""
    result = _git(['status', '--porcelain'], capture=True)
    return len(result.stdout.strip()) == 0


def _is_shallow_repo() -> bool:
    """Return True when git history is shallow."""
    result = _git(['rev-parse', '--is-shallow-repository'], check=False, capture=True)
    return result.returncode == 0 and result.stdout.strip() == 'true'


def commit_release_metadata(version: str, dry_run: bool = False) -> bool:
    """Commit and push release metadata changes on develop, if present.

    This includes version-bearing files and CHANGELOG.md when modified.
    It ensures merge_develop_to_main sees a clean worktree and that the
    release bump commit exists on origin/develop before merging to main.
    """
    if _current_branch() != 'develop':
        logger.error("Release metadata commit requires current branch 'develop'")
        return False

    candidate_paths = [str(spec['path'].relative_to(PROJECT_ROOT))
                       for spec in VERSION_FILES.values()]
    changelog = PROJECT_ROOT / 'CHANGELOG.md'
    if changelog.exists():
        candidate_paths.append('CHANGELOG.md')

    changed_paths = []
    for path in candidate_paths:
        result = _git(['status', '--porcelain', '--', path], capture=True)
        if result.stdout.strip():
            changed_paths.append(path)

    if not changed_paths:
        logger.info("No release metadata changes to commit")
        return True

    if dry_run:
        logger.info(f"[DRY RUN] Would commit and push release metadata: {changed_paths}")
        return True

    tag = f"v{version}"
    commit_message = f"chore(release): bump version to {version}"
    try:
        logger.info(f"Committing release metadata for {tag}...")
        _git(['add'] + changed_paths)
        _git(['commit', '-m', commit_message])
        logger.info("Pushing develop...")
        _git(['push', 'origin', 'develop'])
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to commit release metadata: {e}")
        return False


def merge_develop_to_main(dry_run: bool = False) -> bool:
    """Merge develop into main (gitflow release merge).

    Workflow:
      1. Verify we are on develop with a clean worktree
      2. Checkout main and pull latest
      3. Merge develop into main (no fast-forward for a merge commit)
      4. Push main
      5. Return to develop

    Args:
        dry_run: If True, log what would happen but don't execute.

    Returns:
        True on success, False on failure.
    """
    starting_branch = _current_branch()

    if starting_branch != 'develop':
        logger.error(f"Expected to be on 'develop', currently on '{starting_branch}'")
        return False

    if not _is_clean():
        logger.error("Working tree is not clean — commit or stash changes first")
        return False

    if dry_run:
        logger.info("[DRY RUN] Would merge develop → main and push")
        return True

    try:
        # Ensure full history before merge; shallow clones can trigger false
        # "unrelated histories" failures when merging long-lived branches.
        if _is_shallow_repo():
            logger.info("Repository is shallow; fetching full history...")
            _git(['fetch', '--unshallow', 'origin'], check=False)

        # Pull latest develop
        logger.info("Pulling latest develop...")
        _git(['pull', 'origin', 'develop'])

        # Checkout main and pull
        logger.info("Switching to main...")
        _git(['checkout', 'main'])
        _git(['pull', 'origin', 'main'])

        # Merge develop into main
        logger.info("Merging develop into main...")
        merge_cmd = ['merge', 'develop', '--no-ff', '-m', 'Merge branch \'develop\'']
        merge_result = _git(merge_cmd, check=False, capture=True)
        if merge_result.returncode != 0:
            stderr = (merge_result.stderr or '').strip()
            if 'refusing to merge unrelated histories' in stderr and _is_shallow_repo():
                logger.warning("Merge reported unrelated histories on shallow repo; retrying after unshallow fetch...")
                _git(['fetch', '--unshallow', 'origin'], check=False)
                merge_result = _git(merge_cmd, check=False, capture=True)
            if merge_result.returncode != 0:
                raise subprocess.CalledProcessError(
                    merge_result.returncode,
                    ['git'] + merge_cmd,
                    output=merge_result.stdout,
                    stderr=merge_result.stderr,
                )

        # Push main
        logger.info("Pushing main...")
        _git(['push', 'origin', 'main'])

        # Return to develop
        logger.info("Switching back to develop...")
        _git(['checkout', 'develop'])

        logger.info("Merge develop → main complete")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Merge failed: {e}")
        # Try to return to starting branch
        _git(['checkout', starting_branch], check=False)
        return False


def git_tag_and_push(version: str, message: Optional[str] = None,
                     dry_run: bool = False) -> bool:
    """Create annotated tag on main and push it.

    Must be called after merge_develop_to_main so the tag lands on main.

    Args:
        version: Version string (tag will be vX.Y.Z)
        message: Tag annotation message. Defaults to 'Release vX.Y.Z'.
        dry_run: If True, log what would happen but don't execute.
    """
    tag = f"v{version}"
    msg = message or f"Release {tag}"

    if dry_run:
        logger.info(f"[DRY RUN] Would tag {tag} on main and push")
        return True

    try:
        # Switch to main to tag
        current = _current_branch()
        if current != 'main':
            _git(['checkout', 'main'])

        _git(['tag', '-a', tag, '-m', msg])
        _git(['push', 'origin', '--tags'])
        logger.info(f"Tagged {tag} on main and pushed")

        # Return to develop
        if current != 'main':
            _git(['checkout', current])

        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Tagging failed: {e}")
        return False


def git_commit_and_tag(version: str, message: Optional[str] = None,
                       dry_run: bool = False) -> bool:
    """Commit version file changes, create annotated tag, push both.

    .. deprecated::
        Use merge_develop_to_main + git_tag_and_push for gitflow releases.
        This function is kept for backward compatibility with non-gitflow repos.

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
                        help='Bump type for --release (mutually exclusive with --target-version)')
    parser.add_argument('--target-version', type=str,
                        help='Explicit target version X.Y.Z for --release (validated against current)')
    parser.add_argument('--release-notes', type=str, help='Release notes for --release')
    parser.add_argument('--changelog', action='store_true',
                        help='Use CHANGELOG.md for release notes (instead of --release-notes)')
    parser.add_argument('--skip-tests', action='store_true', help='Skip tests during release')
    parser.add_argument('--skip-github', action='store_true', help='Skip GitHub release creation')
    parser.add_argument('--pypi', action='store_true',
                        help='Upload to PyPI after --build (always on during --release)')
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
        if not args.bump_type and not args.target_version:
            parser.error("--release requires --bump-type or --target-version")
        if args.bump_type and args.target_version:
            parser.error("--bump-type and --target-version are mutually exclusive")
        if not args.release_notes and not args.changelog:
            parser.error("--release requires --release-notes or --changelog")

        # Early check: PyPI token must be available (upload is mandatory)
        pypi_token = args.token or os.environ.get('PYPI_API_TOKEN')
        if not pypi_token and not args.dry_run:
            parser.error(
                "--release requires a PyPI token. "
                "Set PYPI_API_TOKEN env var or pass --token."
            )

        # 1. Check consistency
        logger.info("Step 1/12: Checking version consistency...")
        status = check_consistency()
        if not status['consistent']:
            logger.error(f"Version inconsistency: {status['versions']}")
            sys.exit(1)

        # 1b. Validate target version (if provided)
        if args.target_version:
            try:
                validate_target_version(args.target_version)
            except ValueError as e:
                logger.error(str(e))
                sys.exit(1)

        # 1c. Check CI status
        logger.info("Checking CI status on current branch...")
        if not check_ci_status():
            logger.warning("CI check did not pass — proceeding anyway (verify manually)")

        # 2. Tests
        logger.info("Step 2/12: Running tests...")
        if not args.skip_tests:
            if not run_tests():
                logger.error("Tests failed, aborting release")
                sys.exit(1)
        else:
            logger.info("Tests skipped (--skip-tests)")

        # 3. Set version
        logger.info("Step 3/12: Setting version...")
        if args.target_version:
            new_ver = args.target_version
            current_ver = get_current_version()
            if new_ver == current_ver:
                logger.info(f"Version already at {new_ver} — skipping bump")
            elif args.dry_run:
                logger.info(f"[DRY RUN] Would set version to {new_ver}")
            else:
                set_version(new_ver)
                logger.info(f"Version set to {new_ver}")
        else:
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
        logger.info("Step 4/12: Verifying import...")
        if not args.dry_run:
            if not verify_import():
                logger.error("Import verification failed")
                sys.exit(1)
        else:
            logger.info("[DRY RUN] Would verify import")

        # 5. Clean build artifacts
        logger.info("Step 5/12: Cleaning build artifacts...")
        clean_build_artifacts()

        # 6. Build
        logger.info("Step 6/12: Building package...")
        if not args.dry_run:
            if not build_package():
                sys.exit(1)
        else:
            logger.info("[DRY RUN] Would build package")

        # 7. Validate
        logger.info("Step 7/12: Validating package...")
        if not args.dry_run:
            if not validate_build():
                sys.exit(1)
        else:
            logger.info("[DRY RUN] Would validate package")

        # 8. Resolve release notes (needed for tag + GitHub release)
        logger.info("Step 8/12: Resolving release notes...")
        if args.changelog:
            notes = extract_changelog_notes(new_ver) or extract_changelog_notes('Unreleased')
            if not notes:
                logger.warning("Could not extract changelog notes, using default")
                notes = f"Release v{new_ver}"
        else:
            notes = args.release_notes

        # 8b. Persist release metadata on develop
        logger.info("Committing release metadata on develop...")
        if _current_branch() == 'develop' or args.dry_run:
            if not commit_release_metadata(new_ver, args.dry_run):
                logger.error("Release metadata commit failed")
                sys.exit(1)
        else:
            logger.warning(f"Not on develop (on {_current_branch()}), skipping metadata commit")

        # 9. Merge develop → main (gitflow)
        logger.info("Step 9/12: Merging develop → main...")
        if _current_branch() == 'develop' or args.dry_run:
            if not merge_develop_to_main(args.dry_run):
                logger.error("Merge develop → main failed")
                sys.exit(1)
        else:
            logger.warning(f"Not on develop (on {_current_branch()}), skipping merge")

        # 10. Tag on main + push
        logger.info("Step 10/12: Tagging release on main...")
        if not git_tag_and_push(new_ver, notes, args.dry_run):
            logger.warning("Tagging failed (non-fatal)")

        # 11. Upload to PyPI (mandatory for releases)
        logger.info("Step 11/12: PyPI upload...")
        if not upload_to_pypi(args.repository, args.token, args.dry_run):
            logger.error("PyPI upload failed")
            sys.exit(1)

        # 12. GitHub release
        logger.info("Step 12/12: GitHub release...")
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
