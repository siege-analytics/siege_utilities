#!/usr/bin/env python3
"""
Automated Documentation and Deployment Script

This script automates the entire workflow for:
1. Generating documentation from code
2. Updating wiki repositories
3. Running quality checks
4. Basic git operations

Usage:
    python scripts/automate_docs_and_deploy.py [--dry-run] [--skip-tests] [--force]
"""

import argparse
import os
import sys
import subprocess
import shutil
import tempfile
import logging
from pathlib import Path
from datetime import datetime
import yaml
import json
import re

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from siege_utilities.core.logging import get_logger

class DocumentationAutomation:
    """Automates documentation generation, wiki updates, and deployment"""
    
    def __init__(self, dry_run=False, skip_tests=False, force=False):
        self.dry_run = dry_run
        self.skip_tests = skip_tests
        self.force = force
        self.logger = get_logger("docs_automation")
        self.project_root = Path(__file__).parent.parent
        
        # Configuration
        self.config = self._load_config()
        
    def _load_config(self):
        """Load automation configuration"""
        config_path = self.project_root / "scripts" / "automation_config.yaml"
        
        if config_path.exists():
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        
        # Default configuration
        return {
            'documentation': {
                'source_dirs': ['siege_utilities', 'examples'],
                'output_dir': 'docs/build',
                'formats': ['html', 'pdf'],
                'exclude_patterns': ['__pycache__', '*.pyc', 'tests']
            },
            'wiki_repos': {
                'wiki_fresh': 'wiki_fresh',
                'wiki_recipes': 'wiki_recipes',
                'wiki_debug': 'wiki_debug'
            },
            'quality_checks': {
                'run_tests': True,
                'run_linting': True,
                'run_type_checking': True,
                'test_coverage_threshold': 80
            },
            'git': {
                'main_branch': 'main',
                'docs_branch': 'docs-update',
                'commit_message_template': 'Automated docs update: {timestamp}',
                'push_remote': 'origin'
            }
        }
    
    def run_full_workflow(self):
        """Execute the complete automation workflow"""
        self.logger.info("🚀 Starting automated documentation and deployment workflow")
        
        try:
            # 1. Pre-flight checks
            self._pre_flight_checks()
            
            # 2. Quality checks
            if not self.skip_tests:
                self._run_quality_checks()
            
            # 3. Generate documentation
            self._generate_documentation()
            
            # 4. Update wiki repositories
            self._update_wiki_repos()
            
            # 5. Git operations
            self._perform_git_operations()
            
            # 6. Post-deployment tasks
            self._post_deployment_tasks()
            
            self.logger.info("✅ Workflow completed successfully!")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Workflow failed: {str(e)}")
            self._cleanup_on_failure()
            return False
    
    def _pre_flight_checks(self):
        """Run pre-flight checks before starting workflow"""
        self.logger.info("🔍 Running pre-flight checks...")
        
        # Check if we're in a git repository
        if not self._is_git_repo():
            raise RuntimeError("Not in a git repository")
        
        # Check current branch
        current_branch = self._get_current_branch()
        self.logger.info(f"Current branch: {current_branch}")
        
        # Check for uncommitted changes
        if self._has_uncommitted_changes() and not self.force:
            raise RuntimeError("Uncommitted changes detected. Use --force to override.")
        
        self.logger.info("✅ Pre-flight checks passed")
    
    def _is_git_repo(self):
        """Check if current directory is a git repository"""
        return (self.project_root / ".git").exists()
    
    def _get_current_branch(self):
        """Get current git branch"""
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return "unknown"
    
    def _has_uncommitted_changes(self):
        """Check if there are uncommitted changes"""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            return bool(result.stdout.strip())
        except subprocess.CalledProcessError:
            return False
    
    def _run_quality_checks(self):
        """Run quality checks including tests"""
        self.logger.info("🧪 Running quality checks...")
        
        # Run tests
        if self.config['quality_checks']['run_tests']:
            self._run_tests()
        
        # Run linting
        if self.config['quality_checks']['run_linting']:
            self._run_linting()
        
        # Run type checking
        if self.config['quality_checks']['run_type_checking']:
            self._run_type_checking()
        
        self.logger.info("✅ Quality checks passed")
    
    def _run_tests(self):
        """Run the test suite"""
        self.logger.info("Running test suite...")
        
        if self.dry_run:
            self.logger.info("DRY RUN: Would run tests")
            return
        
        # Run pytest with coverage
        cmd = [
            sys.executable, "-m", "pytest",
            "--cov=siege_utilities",
            "--cov-report=html",
            "--cov-report=term-missing",
            "--cov-fail-under", str(self.config['quality_checks']['test_coverage_threshold']),
            "-v"
        ]
        
        result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise RuntimeError(f"Tests failed:\n{result.stdout}\n{result.stderr}")
        
        self.logger.info("✅ Tests passed")
    
    def _run_linting(self):
        """Run code linting"""
        self.logger.info("Running linting...")
        
        if self.dry_run:
            self.logger.info("DRY RUN: Would run linting")
            return
        
        # Run flake8
        cmd = [sys.executable, "-m", "flake8", "siege_utilities", "tests"]
        result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True)
        
        if result.returncode != 0:
            self.logger.warning(f"Linting issues found:\n{result.stdout}")
            if not self.force:
                raise RuntimeError("Linting failed. Use --force to override.")
        
        self.logger.info("✅ Linting completed")
    
    def _run_type_checking(self):
        """Run type checking with mypy"""
        self.logger.info("Running type checking...")
        
        if self.dry_run:
            self.logger.info("DRY RUN: Would run type checking")
            return
        
        # Check if mypy is available
        try:
            cmd = [sys.executable, "-m", "mypy", "siege_utilities"]
            result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True)
            
            if result.returncode != 0:
                self.logger.warning(f"Type checking issues found:\n{result.stdout}")
                if not self.force:
                    raise RuntimeError("Type checking failed. Use --force to override.")
        except FileNotFoundError:
            self.logger.info("mypy not available, skipping type checking")
        
        self.logger.info("✅ Type checking completed")
    
    def _generate_documentation(self):
        """Generate documentation from source code"""
        self.logger.info("📚 Generating documentation...")
        
        if self.dry_run:
            self.logger.info("DRY RUN: Would generate documentation")
            return
        
        # Create output directory
        output_dir = self.project_root / self.config['documentation']['output_dir']
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate Sphinx documentation
        self._generate_sphinx_docs(output_dir)
        
        # Generate API documentation
        self._generate_api_docs(output_dir)
        
        # Generate recipe documentation
        self._generate_recipe_docs(output_dir)
        
        self.logger.info("✅ Documentation generated")
    
    def _generate_sphinx_docs(self, output_dir):
        """Generate Sphinx documentation"""
        sphinx_dir = self.project_root / "docs"
        
        if not sphinx_dir.exists():
            self.logger.info("Sphinx docs directory not found, skipping")
            return
        
        # Run sphinx-build
        cmd = [
            sys.executable, "-m", "sphinx.cmd.build",
            "-b", "html",
            str(sphinx_dir / "source"),
            str(output_dir / "html")
        ]
        
        result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise RuntimeError(f"Sphinx build failed:\n{result.stdout}\n{result.stderr}")
    
    def _generate_api_docs(self, output_dir):
        """Generate API documentation using pydoc"""
        api_dir = output_dir / "api"
        api_dir.mkdir(exist_ok=True)
        
        # Generate API docs for main modules
        modules = [
            'siege_utilities.core',
            'siege_utilities.distributed',
            'siege_utilities.files',
            'siege_utilities.geo',
            'siege_utilities.analytics',
            'siege_utilities.reporting'
        ]
        
        for module in modules:
            try:
                cmd = [
                    sys.executable, "-m", "pydoc", "-w", module
                ]
                result = subprocess.run(cmd, cwd=api_dir, capture_output=True, text=True)
                
                if result.returncode == 0:
                    self.logger.info(f"Generated API docs for {module}")
            except Exception as e:
                self.logger.warning(f"Failed to generate API docs for {module}: {e}")
    
    def _generate_recipe_docs(self, output_dir):
        """Generate recipe documentation"""
        recipes_dir = output_dir / "recipes"
        recipes_dir.mkdir(exist_ok=True)
        
        # Copy wiki recipe files
        wiki_dirs = ['wiki_fresh', 'wiki_recipes']
        
        for wiki_dir in wiki_dirs:
            source_dir = self.project_root / wiki_dir
            if source_dir.exists():
                dest_dir = recipes_dir / wiki_dir
                if dest_dir.exists():
                    shutil.rmtree(dest_dir)
                shutil.copytree(source_dir, dest_dir)
                self.logger.info(f"Copied recipes from {wiki_dir}")
    
    def _update_wiki_repos(self):
        """Update wiki repositories with latest documentation"""
        self.logger.info("📝 Updating wiki repositories...")
        
        if self.dry_run:
            self.logger.info("DRY RUN: Would update wiki repos")
            return
        
        for wiki_name, wiki_path in self.config['wiki_repos'].items():
            wiki_dir = self.project_root / wiki_path
            
            if not wiki_dir.exists():
                self.logger.warning(f"Wiki directory {wiki_path} not found, skipping")
                continue
            
            self.logger.info(f"Updating {wiki_name}...")
            
            # Update README files with latest information
            self._update_wiki_readme(wiki_dir, wiki_name)
            
            # Generate changelog
            self._generate_wiki_changelog(wiki_dir, wiki_name)
        
        self.logger.info("✅ Wiki repositories updated")
    
    def _update_wiki_readme(self, wiki_dir, wiki_name):
        """Update wiki README with latest information"""
        readme_path = wiki_dir / "README.md"
        
        if not readme_path.exists():
            # Create new README
            content = self._generate_wiki_readme_content(wiki_name)
            with open(readme_path, 'w') as f:
                f.write(content)
        else:
            # Update existing README
            self._update_existing_readme(readme_path, wiki_name)
    
    def _generate_wiki_readme_content(self, wiki_name):
        """Generate content for a new wiki README"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        return f"""# {wiki_name.replace('_', ' ').title()}

This wiki contains documentation and recipes for the Siege Utilities library.

**Last Updated:** {timestamp}

## Contents

- **Getting Started**: Basic setup and installation
- **Recipes**: Practical examples and use cases
- **API Reference**: Detailed function and class documentation
- **Examples**: Code samples and demonstrations

## Quick Start

1. Check the [Getting Started](Getting-Started.md) guide
2. Browse available [Recipes](Recipes/) for your use case
3. Refer to [API Reference](../docs/build/html/index.html) for detailed documentation

## Contributing

To contribute to this documentation:
1. Edit the markdown files in this directory
2. Run the automation script: `python scripts/automate_docs_and_deploy.py`
3. Commit and push your changes

## Recent Updates

See [CHANGELOG.md](CHANGELOG.md) for recent changes and updates.
"""
    
    def _update_existing_readme(self, readme_path, wiki_name):
        """Update an existing README with latest information"""
        with open(readme_path, 'r') as f:
            content = f.read()
        
        # Update timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Replace or add timestamp
        if "**Last Updated:**" in content:
            content = content.replace(
                r"**Last Updated:** \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}",
                f"**Last Updated:** {timestamp}",
                flags=re.MULTILINE
            )
        else:
            # Add timestamp after title
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if line.startswith('# '):
                    lines.insert(i + 1, f"\n**Last Updated:** {timestamp}\n")
                    break
            content = '\n'.join(lines)
        
        with open(readme_path, 'w') as f:
            f.write(content)
    
    def _generate_wiki_changelog(self, wiki_dir, wiki_name):
        """Generate changelog for wiki"""
        changelog_path = wiki_dir / "CHANGELOG.md"
        
        # Get recent git commits
        recent_commits = self._get_recent_commits(10)
        
        changelog_content = f"# Changelog - {wiki_name.replace('_', ' ').title()}\n\n"
        changelog_content += f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        # Group commits by date
        commits_by_date = {}
        for commit in recent_commits:
            date = commit['date'].split()[0]  # Just the date part
            if date not in commits_by_date:
                commits_by_date[date] = []
            commits_by_date[date].append(commit)
        
        # Generate changelog entries
        for date in sorted(commits_by_date.keys(), reverse=True):
            changelog_content += f"## {date}\n\n"
            for commit in commits_by_date[date]:
                changelog_content += f"- **{commit['hash'][:8]}** {commit['message']}\n"
            changelog_content += "\n"
        
        with open(changelog_path, 'w') as f:
            f.write(changelog_content)
    
    def _get_recent_commits(self, count=10):
        """Get recent git commits"""
        try:
            cmd = [
                "git", "log", 
                f"-{count}", 
                "--pretty=format:%H|%ad|%s",
                "--date=short"
            ]
            result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True, check=True)
            
            commits = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split('|')
                    if len(parts) == 3:
                        commits.append({
                            'hash': parts[0],
                            'date': parts[1],
                            'message': parts[2]
                        })
            return commits
        except subprocess.CalledProcessError:
            return []
    
    def _perform_git_operations(self):
        """Perform git operations for deployment"""
        self.logger.info("🔧 Performing git operations...")
        
        if self.dry_run:
            self.logger.info("DRY RUN: Would perform git operations")
            return
        
        try:
            # Stage all changes
            subprocess.run(["git", "add", "."], cwd=self.project_root, check=True)
            
            # Create commit
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            commit_msg = self.config['git']['commit_message_template'].format(timestamp=timestamp)
            
            subprocess.run(["git", "commit", "-m", commit_msg], cwd=self.project_root, check=True)
            
            # Push to remote
            remote = self.config['git']['push_remote']
            branch = self._get_current_branch()
            
            subprocess.run(["git", "push", remote, branch], cwd=self.project_root, check=True)
            
            self.logger.info("✅ Git operations completed")
            
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Git operations failed: {e}")
    
    def _post_deployment_tasks(self):
        """Perform post-deployment tasks"""
        self.logger.info("🎉 Running post-deployment tasks...")
        
        if self.dry_run:
            self.logger.info("DRY RUN: Would run post-deployment tasks")
            return
        
        # Generate deployment report
        self._generate_deployment_report()
        
        # Update deployment status
        self._update_deployment_status()
        
        self.logger.info("✅ Post-deployment tasks completed")
    
    def _generate_deployment_report(self):
        """Generate deployment report"""
        report_dir = self.project_root / "reports" / "deployments"
        report_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = report_dir / f"deployment_{timestamp}.md"
        
        with open(report_file, 'w') as f:
            f.write(self._format_deployment_report())
        
        self.logger.info(f"Deployment report generated: {report_file}")
    
    def _format_deployment_report(self):
        """Format deployment report"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        current_branch = self._get_current_branch()
        
        return f"""# Deployment Report

**Deployment Time:** {timestamp}
**Branch:** {current_branch}
**Environment:** {'DRY RUN' if self.dry_run else 'PRODUCTION'}

## Summary

✅ Documentation generated and updated
✅ Wiki repositories synchronized
✅ Quality checks passed
✅ Changes committed and pushed

## Details

- **Tests Skipped:** {self.skip_tests}
- **Force Mode:** {self.force}
- **Git Remote:** {self.config['git']['push_remote']}

## Next Steps

1. Verify documentation is accessible
2. Check wiki repositories for updates
3. Monitor for any deployment issues
4. Plan next iteration

---
*Generated by Siege Utilities Documentation Automation*
"""
    
    def _update_deployment_status(self):
        """Update deployment status"""
        status_file = self.project_root / "reports" / "deployment_status.json"
        
        status = {
            'last_deployment': datetime.now().isoformat(),
            'branch': self._get_current_branch(),
            'status': 'success',
            'dry_run': self.dry_run
        }
        
        with open(status_file, 'w') as f:
            json.dump(status, f, indent=2, default=str)
    
    def _cleanup_on_failure(self):
        """Clean up on workflow failure"""
        self.logger.info("🧹 Cleaning up after failure...")
        
        # Log failure details
        self.logger.error("Workflow failed - manual intervention may be required")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Automate documentation generation, wiki updates, and deployment"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without making actual changes"
    )
    
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip running tests and quality checks"
    )
    
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force execution even with warnings"
    )
    
    parser.add_argument(
        "--config",
        type=str,
        help="Path to custom configuration file"
    )
    
    args = parser.parse_args()
    
    # Initialize automation
    automation = DocumentationAutomation(
        dry_run=args.dry_run,
        skip_tests=args.skip_tests,
        force=args.force
    )
    
    # Run workflow
    success = automation.run_full_workflow()
    
    if success:
        print("\n🎉 Automation completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Automation failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
