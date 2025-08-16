#!/usr/bin/env python3
"""
Release Manager
Comprehensive system to manage releases across GitHub and PyPI
"""

import os
import sys
import subprocess
import json
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import argparse
from datetime import datetime
import requests
from packaging import version

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ReleaseManager:
    """Manages releases across GitHub and PyPI"""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.setup_py = self.project_root / "setup.py"
        self.readme = self.project_root / "README.md"
        self.changelog = self.project_root / "CHANGELOG.md"
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.pypi_token = os.getenv("PYPI_TOKEN")
        
    def get_current_version(self) -> str:
        """Get current version from setup.py"""
        if not self.setup_py.exists():
            raise FileNotFoundError("setup.py not found")
        
        with open(self.setup_py, 'r') as f:
            content = f.read()
        
        # Look for version in setup.py
        version_match = re.search(r'version=["\']([^"\']+)["\']', content)
        if version_match:
            return version_match.group(1)
        
        raise ValueError("Could not find version in setup.py")
    
    def get_latest_github_release(self) -> Optional[Dict]:
        """Get latest GitHub release information"""
        if not self.github_token:
            logger.warning("GITHUB_TOKEN not set, cannot check GitHub releases")
            return None
        
        try:
            headers = {
                "Authorization": f"token {self.github_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            response = requests.get(
                "https://api.github.com/repos/siege-analytics/siege_utilities/releases/latest",
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to get GitHub release: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting GitHub release: {e}")
            return None
    
    def get_latest_pypi_release(self) -> Optional[str]:
        """Get latest PyPI release version"""
        try:
            response = requests.get("https://pypi.org/pypi/siege-utilities/json")
            
            if response.status_code == 200:
                data = response.json()
                return data["info"]["version"]
            else:
                logger.warning(f"Failed to get PyPI info: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting PyPI info: {e}")
            return None
    
    def check_version_consistency(self) -> Dict[str, any]:
        """Check if versions are consistent across platforms"""
        current = self.get_current_version()
        github_release = self.get_latest_github_release()
        pypi_release = self.get_latest_pypi_release()
        
        status = {
            "current_version": current,
            "github_version": github_release["tag_name"].lstrip("v") if github_release else None,
            "pypi_version": pypi_release,
            "consistent": True,
            "issues": []
        }
        
        # Check GitHub consistency
        if github_release and github_release["tag_name"].lstrip("v") != current:
            status["consistent"] = False
            status["issues"].append(f"GitHub release version ({github_release['tag_name']}) doesn't match current version ({current})")
        
        # Check PyPI consistency
        if pypi_release and pypi_release != current:
            status["consistent"] = False
            status["issues"].append(f"PyPI version ({pypi_release}) doesn't match current version ({current})")
        
        return status
    
    def bump_version(self, bump_type: str) -> str:
        """Bump version according to semantic versioning"""
        current = self.get_current_version()
        current_ver = version.parse(current)
        
        if bump_type == "major":
            new_ver = version.Version(f"{current_ver.major + 1}.0.0")
        elif bump_type == "minor":
            new_ver = version.Version(f"{current_ver.major}.{current_ver.minor + 1}.0")
        elif bump_type == "patch":
            new_ver = version.Version(f"{current_ver.major}.{current_ver.minor}.{current_ver.micro + 1}")
        else:
            raise ValueError(f"Invalid bump type: {bump_type}")
        
        new_version = str(new_ver)
        
        # Update setup.py
        with open(self.setup_py, 'r') as f:
            content = f.read()
        
        content = re.sub(
            r'version=["\']([^"\']+)["\']',
            f'version="{new_version}"',
            content
        )
        
        with open(self.setup_py, 'w') as f:
            f.write(content)
        
        logger.info(f"Version bumped from {current} to {new_version}")
        return new_version
    
    def update_changelog(self, new_version: str, release_notes: str):
        """Update CHANGELOG.md with new release"""
        if not self.changelog.exists():
            self.changelog.write_text("# Changelog\n\n")
        
        with open(self.changelog, 'r') as f:
            content = f.read()
        
        # Add new release at the top
        release_header = f"## [{new_version}] - {datetime.now().strftime('%Y-%m-%d')}\n\n"
        release_content = f"{release_notes}\n\n"
        
        # Find the position after the title
        lines = content.split('\n')
        insert_pos = 1  # After the title
        
        for i, line in enumerate(lines):
            if line.startswith('## ['):
                insert_pos = i
                break
        
        lines.insert(insert_pos, release_header)
        lines.insert(insert_pos + 1, release_content)
        
        with open(self.changelog, 'w') as f:
            f.write('\n'.join(lines))
        
        logger.info(f"Changelog updated for version {new_version}")
    
    def build_package(self) -> bool:
        """Build the Python package"""
        try:
            logger.info("Building Python package...")
            
            # Clean previous builds
            subprocess.run([sys.executable, "setup.py", "clean", "--all"], 
                         cwd=self.project_root, check=True)
            
            # Build package
            subprocess.run([sys.executable, "setup.py", "sdist", "bdist_wheel"], 
                         cwd=self.project_root, check=True)
            
            logger.info("Package built successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to build package: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error building package: {e}")
            return False
    
    def upload_to_pypi(self) -> bool:
        """Upload package to PyPI"""
        if not self.pypi_token:
            logger.error("PYPI_TOKEN not set, cannot upload to PyPI")
            return False
        
        try:
            logger.info("Uploading to PyPI...")
            
            # Install twine if not available
            try:
                import twine
            except ImportError:
                subprocess.run([sys.executable, "-m", "pip", "install", "twine"], check=True)
            
            # Upload using twine
            subprocess.run([
                sys.executable, "-m", "twine", "upload",
                "--username", "__token__",
                "--password", self.pypi_token,
                "dist/*"
            ], cwd=self.project_root, check=True)
            
            logger.info("Package uploaded to PyPI successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to upload to PyPI: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error uploading to PyPI: {e}")
            return False
    
    def create_github_release(self, version: str, release_notes: str) -> bool:
        """Create GitHub release"""
        if not self.github_token:
            logger.error("GITHUB_TOKEN not set, cannot create GitHub release")
            return False
        
        try:
            logger.info("Creating GitHub release...")
            
            # Create release data
            release_data = {
                "tag_name": f"v{version}",
                "name": f"Release {version}",
                "body": release_notes,
                "draft": False,
                "prerelease": False
            }
            
            headers = {
                "Authorization": f"token {self.github_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            response = requests.post(
                "https://api.github.com/repos/siege-analytics/siege_utilities/releases",
                headers=headers,
                json=release_data
            )
            
            if response.status_code == 201:
                logger.info("GitHub release created successfully")
                return True
            else:
                logger.error(f"Failed to create GitHub release: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating GitHub release: {e}")
            return False
    
    def run_tests(self) -> bool:
        """Run the test suite"""
        try:
            logger.info("Running tests...")
            
            # Run pytest
            result = subprocess.run([sys.executable, "-m", "pytest"], 
                                 cwd=self.project_root, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("All tests passed")
                return True
            else:
                logger.error("Tests failed")
                logger.error(f"stdout: {result.stdout}")
                logger.error(f"stderr: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error running tests: {e}")
            return False
    
    def commit_and_tag(self, version: str, commit_message: str) -> bool:
        """Commit changes and create git tag"""
        try:
            logger.info("Committing changes and creating tag...")
            
            # Add all changes
            subprocess.run(["git", "add", "."], cwd=self.project_root, check=True)
            
            # Commit
            subprocess.run(["git", "commit", "-m", commit_message], 
                         cwd=self.project_root, check=True)
            
            # Create tag
            subprocess.run(["git", "tag", f"v{version}"], 
                         cwd=self.project_root, check=True)
            
            logger.info("Changes committed and tagged successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Git operation failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error in git operations: {e}")
            return False
    
    def push_release(self, version: str) -> bool:
        """Push changes and tags to remote"""
        try:
            logger.info("Pushing to remote...")
            
            # Push changes
            subprocess.run(["git", "push", "origin", "main"], 
                         cwd=self.project_root, check=True)
            
            # Push tags
            subprocess.run(["git", "push", "origin", f"v{version}"], 
                         cwd=self.project_root, check=True)
            
            logger.info("Changes pushed to remote successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to push to remote: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error pushing to remote: {e}")
            return False
    
    def full_release(self, bump_type: str, release_notes: str, 
                    skip_tests: bool = False, skip_pypi: bool = False) -> bool:
        """Perform a full release process"""
        logger.info("Starting full release process...")
        
        try:
            # 1. Check current state
            status = self.check_version_consistency()
            if not status["consistent"]:
                logger.error("Version inconsistency detected:")
                for issue in status["issues"]:
                    logger.error(f"  - {issue}")
                return False
            
            # 2. Run tests (unless skipped)
            if not skip_tests:
                if not self.run_tests():
                    logger.error("Tests failed, aborting release")
                    return False
            
            # 3. Bump version
            new_version = self.bump_version(bump_type)
            
            # 4. Update changelog
            self.update_changelog(new_version, release_notes)
            
            # 5. Build package
            if not self.build_package():
                logger.error("Failed to build package")
                return False
            
            # 6. Upload to PyPI (unless skipped)
            if not skip_pypi:
                if not self.upload_to_pypi():
                    logger.error("Failed to upload to PyPI")
                    return False
            
            # 7. Commit and tag
            commit_message = f"Release {new_version}\n\n{release_notes}"
            if not self.commit_and_tag(new_version, commit_message):
                logger.error("Failed to commit and tag")
                return False
            
            # 8. Create GitHub release
            if not self.create_github_release(new_version, release_notes):
                logger.error("Failed to create GitHub release")
                return False
            
            # 9. Push to remote
            if not self.push_release(new_version):
                logger.error("Failed to push to remote")
                return False
            
            logger.info(f"Release {new_version} completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Release process failed: {e}")
            return False

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Release Manager for Siege Utilities")
    parser.add_argument("--check", action="store_true",
                       help="Check version consistency")
    parser.add_argument("--bump", choices=["major", "minor", "patch"],
                       help="Bump version")
    parser.add_argument("--release", action="store_true",
                       help="Perform full release")
    parser.add_argument("--bump-type", choices=["major", "minor", "patch"],
                       help="Version bump type for release")
    parser.add_argument("--release-notes", type=str,
                       help="Release notes for the new version")
    parser.add_argument("--skip-tests", action="store_true",
                       help="Skip running tests during release")
    parser.add_argument("--skip-pypi", action="store_true",
                       help="Skip PyPI upload during release")
    parser.add_argument("--build", action="store_true",
                       help="Build package only")
    parser.add_argument("--upload-pypi", action="store_true",
                       help="Upload to PyPI only")
    
    args = parser.parse_args()
    
    manager = ReleaseManager()
    
    try:
        if args.check:
            status = manager.check_version_consistency()
            print(json.dumps(status, indent=2))
            
        elif args.bump:
            new_version = manager.bump_version(args.bump)
            print(f"Version bumped to {new_version}")
            
        elif args.build:
            success = manager.build_package()
            sys.exit(0 if success else 1)
            
        elif args.upload_pypi:
            success = manager.upload_to_pypi()
            sys.exit(0 if success else 1)
            
        elif args.release:
            if not args.bump_type or not args.release_notes:
                parser.error("--release requires --bump-type and --release-notes")
            
            success = manager.full_release(
                args.bump_type,
                args.release_notes,
                skip_tests=args.skip_tests,
                skip_pypi=args.skip_pypi
            )
            sys.exit(0 if success else 1)
            
        else:
            parser.print_help()
            
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
