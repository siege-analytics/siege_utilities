# Release Management System

## Overview

The Siege Utilities Release Management System provides automated, consistent releases across GitHub and PyPI. It ensures version consistency, automates the release process, and maintains proper documentation.

## Features

### 🔄 **Version Consistency**
- **Cross-Platform Sync**: Ensures GitHub releases and PyPI packages have matching versions
- **Automatic Detection**: Identifies version mismatches across platforms
- **Semantic Versioning**: Supports major, minor, and patch version bumps

### 🚀 **Automated Release Process**
- **Full Automation**: Complete release pipeline from version bump to deployment
- **Test Integration**: Runs test suite before release
- **Documentation Updates**: Automatically updates CHANGELOG.md
- **Git Operations**: Handles commits, tags, and pushes

### 🛠️ **Flexible Operations**
- **Individual Steps**: Run specific parts of the release process
- **Skip Options**: Bypass tests or PyPI upload when needed
- **Manual Override**: Force releases regardless of interval

## Quick Start

### 1. **Check Current Status**
```bash
# Check version consistency across platforms
./scripts/release.sh check

# Or use Python directly
python scripts/release_manager.py --check
```

### 2. **Bump Version**
```bash
# Bump minor version (1.0.0 → 1.1.0)
./scripts/release.sh bump minor

# Bump patch version (1.0.0 → 1.0.1)
./scripts/release.sh bump patch

# Bump major version (1.0.0 → 2.0.0)
./scripts/release.sh bump major
```

### 3. **Build Package**
```bash
# Build Python package (source and wheel)
./scripts/release.sh build
```

### 4. **Upload to PyPI**
```bash
# Upload built package to PyPI
./scripts/release.sh upload-pypi
```

### 5. **Full Release**
```bash
# Complete release process
./scripts/release.sh release minor "New features and improvements"
```

## Environment Setup

### Required Environment Variables

```bash
# GitHub API token for creating releases
export GITHUB_TOKEN="ghp_your_token_here"

# PyPI API token for uploading packages
export PYPI_TOKEN="pypi_your_token_here"
```

### Token Setup

#### GitHub Token
1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Generate new token with `repo` scope
3. Copy token and set environment variable

#### PyPI Token
1. Go to PyPI Account Settings → API tokens
2. Create new token with upload permissions
3. Copy token and set environment variable

## Detailed Usage

### Command Line Interface

#### Check Commands
```bash
# Check version consistency
./scripts/release.sh check

# Show current configuration
python scripts/release_manager.py --config
```

#### Version Management
```bash
# Bump version in setup.py
./scripts/release.sh bump [major|minor|patch]

# Check current version
python scripts/release_manager.py --check
```

#### Package Operations
```bash
# Build package only
./scripts/release.sh build

# Upload to PyPI only
./scripts/release.sh upload-pypi
```

#### Full Release
```bash
# Complete release with notes
./scripts/release.sh release [type] "Release notes"

# Examples:
./scripts/release.sh release patch "Bug fixes and improvements"
./scripts/release.sh release minor "New features added"
./scripts/release.sh release major "Breaking changes and major updates"
```

### Python API

```python
from scripts.release_manager import ReleaseManager

# Initialize manager
manager = ReleaseManager()

# Check versions
status = manager.check_version_consistency()
print(f"Versions consistent: {status['consistent']}")

# Bump version
new_version = manager.bump_version("minor")
print(f"New version: {new_version}")

# Build package
success = manager.build_package()

# Create release
success = manager.full_release(
    "minor",
    "New features and improvements"
)
```

## Release Process Flow

### 1. **Pre-Release Checks**
- Verify version consistency across platforms
- Run test suite (unless skipped)
- Check environment variables

### 2. **Version Management**
- Bump version according to semantic versioning
- Update setup.py with new version
- Update CHANGELOG.md with release notes

### 3. **Package Building**
- Clean previous builds
- Build source distribution (sdist)
- Build wheel distribution (bdist_wheel)

### 4. **Distribution**
- Upload to PyPI (unless skipped)
- Create GitHub release with notes
- Commit changes and create git tag

### 5. **Finalization**
- Push changes to remote repository
- Push tags to remote repository
- Update sync logs and configuration

## Configuration

### Wiki Sync Configuration
```json
{
  "last_sync": "2024-08-16T14:30:00",
  "sync_interval_hours": 24,
  "auto_commit": true,
  "auto_push": false,
  "backup_enabled": true,
  "excluded_files": [".git", ".gitignore", "*.tmp"],
  "included_directories": ["Recipes", "Architecture", "Examples"]
}
```

### Release Configuration
The release manager uses environment variables and project structure:
- `GITHUB_TOKEN`: For GitHub API access
- `PYPI_TOKEN`: For PyPI uploads
- `setup.py`: For version information
- `CHANGELOG.md`: For release history

## GitHub Actions Integration

### Automated Wiki Updates
```yaml
name: Update Wiki
on:
  push:
    branches: [ main ]
    paths:
      - 'wiki_fresh/**'
      - 'scripts/update_wiki.py'
  workflow_dispatch:
    inputs:
      force_update:
        description: 'Force update regardless of interval'
        required: false
        default: false
        type: boolean

jobs:
  update-wiki:
    runs-on: ubuntu-latest
    steps:
    - name: Checkout repository
      uses: actions/checkout@v4
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    - name: Update Wiki
      run: python scripts/update_wiki.py --force --auto-push
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Automated Releases
```yaml
name: Release
on:
  push:
    tags:
      - 'v*'
  workflow_dispatch:

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
    - name: Checkout
      uses: actions/checkout@v4
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    - name: Build and Release
      run: |
        python scripts/release_manager.py --release \
          --bump-type patch \
          --release-notes "Automated release"
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        PYPI_TOKEN: ${{ secrets.PYPI_TOKEN }}
```

## Best Practices

### 1. **Version Management**
- Use semantic versioning consistently
- Bump major version for breaking changes
- Bump minor version for new features
- Bump patch version for bug fixes

### 2. **Release Notes**
- Write clear, descriptive release notes
- Include breaking changes prominently
- List new features and improvements
- Mention bug fixes and security updates

### 3. **Testing**
- Always run tests before release
- Use `--skip-tests` only for emergency releases
- Verify functionality in staging environment

### 4. **Documentation**
- Update CHANGELOG.md with each release
- Keep release notes in sync with code changes
- Document breaking changes clearly

### 5. **Security**
- Never commit tokens to version control
- Use environment variables for sensitive data
- Rotate tokens regularly

## Troubleshooting

### Common Issues

#### Version Mismatch
```bash
# Check current versions
./scripts/release.sh check

# Manually sync versions if needed
./scripts/release.sh bump patch
```

#### Build Failures
```bash
# Clean previous builds
python setup.py clean --all

# Check dependencies
pip install -r requirements.txt

# Try building again
./scripts/release.sh build
```

#### Upload Failures
```bash
# Verify PyPI token
echo $PYPI_TOKEN

# Check package format
python -m twine check dist/*

# Try upload again
./scripts/release.sh upload-pypi
```

#### Git Issues
```bash
# Check git status
git status

# Verify remote configuration
git remote -v

# Check authentication
git push origin main --dry-run
```

### Debug Mode
```bash
# Enable debug logging
export PYTHONPATH=.
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from scripts.release_manager import ReleaseManager
manager = ReleaseManager()
manager.check_version_consistency()
"
```

## Integration with Other Systems

### Wiki Synchronization
The release system integrates with the wiki update system:
- Automatic wiki updates after releases
- Synchronized documentation across platforms
- Backup and version control for wiki content

### CI/CD Integration
- GitHub Actions for automated workflows
- Automated testing and deployment
- Continuous integration with release process

### Documentation Systems
- Sphinx documentation generation
- Wiki content management
- Changelog maintenance

## Future Enhancements

### Planned Features
- **Multi-Platform Support**: Support for additional package managers
- **Release Templates**: Predefined release note templates
- **Rollback Support**: Ability to rollback releases
- **Metrics Dashboard**: Release analytics and reporting

### Integration Opportunities
- **Slack Notifications**: Release notifications to team channels
- **Jira Integration**: Automatic ticket updates
- **Docker Support**: Container image releases
- **Helm Charts**: Kubernetes chart releases

## Support and Maintenance

### Getting Help
- Check this documentation first
- Review error logs and debug output
- Test with minimal configuration
- Verify environment setup

### Contributing
- Report bugs and issues
- Suggest improvements
- Submit pull requests
- Update documentation

### Maintenance
- Regular token rotation
- Dependency updates
- Security audits
- Performance monitoring

## Conclusion

The Release Management System provides a robust, automated approach to managing releases across multiple platforms. By following the best practices and using the provided tools, you can ensure consistent, reliable releases that maintain quality and documentation standards.

For additional support or questions, please refer to the project documentation or create an issue in the repository.
