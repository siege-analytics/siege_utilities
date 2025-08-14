# Documentation Automation Scripts

This directory contains automation scripts for streamlining the documentation generation, wiki updates, and deployment workflow for the Siege Utilities library.

## 🚀 Quick Start

### Using the Shell Wrapper (Recommended)

```bash
# Generate documentation and update wikis
./scripts/auto_docs.sh docs

# Full deployment workflow
./scripts/auto_docs.sh deploy

# Run tests only
./scripts/auto_docs.sh test

# Update wikis only
./scripts/auto_docs.sh wiki

# Update branch status only
./scripts/auto_docs.sh status

# Show help
./scripts/auto_docs.sh help
```

### Using Python Directly

```bash
# Basic usage
python scripts/automate_docs_and_deploy.py

# Dry run (no actual changes)
python scripts/automate_docs_and_deploy.py --dry-run

# Skip tests
python scripts/automate_docs_and_deploy.py --skip-tests

# Force execution
python scripts/automate_docs_and_deploy.py --force
```

## 📋 What the Automation Does

The automation script performs the following workflow:

1. **Pre-flight Checks** 🔍
   - Verifies git repository status
   - Checks for uncommitted changes
   - Validates remote access

2. **Quality Checks** 🧪
   - Runs the full test suite with coverage
   - Performs code linting (flake8)
   - Runs type checking (mypy)

3. **Documentation Generation** 📚
   - Generates Sphinx documentation
   - Creates API documentation using pydoc
   - Copies recipe documentation

4. **Wiki Updates** 📝
   - Updates README files with timestamps
   - Generates changelogs from git history
   - Synchronizes across wiki repositories

5. **Branch Status Updates** 🌿
   - Updates branch status using library commands
   - Generates status reports
   - Analyzes branch health

6. **Git Operations** 🔧
   - Stages all changes
   - Creates commits with timestamps
   - Pushes to remote repository

7. **Post-deployment Tasks** 🎉
   - Generates deployment reports
   - Updates deployment status
   - Cleans up temporary files

## ⚙️ Configuration

The automation is configured via `automation_config.yaml`. Key configuration sections:

### Documentation Settings
```yaml
documentation:
  source_dirs: [siege_utilities, examples, scripts]
  output_dir: docs/build
  formats: [html, pdf]
  exclude_patterns: [__pycache__, *.pyc, tests]
```

### Wiki Repository Settings
```yaml
wiki_repos:
  wiki_fresh: wiki_fresh
  wiki_recipes: wiki_recipes
  wiki_debug: wiki_debug
```

### Quality Check Settings
```yaml
quality_checks:
  run_tests: true
  run_linting: true
  run_type_checking: true
  test_coverage_threshold: 80
```

### Git Settings
```yaml
git:
  main_branch: main
  docs_branch: docs-update
  commit_message_template: "Automated docs update: {timestamp}"
  push_remote: origin
```

## 🔧 Customization

### Adding New Wiki Repositories

1. Add the repository to `automation_config.yaml`:
```yaml
wiki_repos:
  new_wiki: path/to/new_wiki
```

2. The script will automatically detect and update the new repository.

### Customizing Documentation Generation

Modify the `_generate_documentation()` method in the Python script to add new documentation types or modify existing ones.

### Adding New Quality Checks

Extend the `_run_quality_checks()` method to include additional validation steps like:
- Security scanning
- Dependency vulnerability checks
- Performance benchmarking

## 📊 Reports and Outputs

The automation generates several types of reports:

### Documentation Output
- **Sphinx HTML**: `docs/build/html/`
- **API Documentation**: `docs/build/api/`
- **Recipe Documentation**: `docs/build/recipes/`

### Status Reports
- **Branch Status**: `reports/branch_status/`
- **Deployment Reports**: `reports/deployments/`
- **Deployment Status**: `reports/deployment_status.json`

### Wiki Updates
- **README files**: Updated with timestamps
- **CHANGELOG.md**: Generated from git history
- **Index files**: Updated navigation

## 🚨 Error Handling

The automation includes robust error handling:

- **Pre-flight validation** prevents common issues
- **Rollback mechanisms** for failed deployments
- **Detailed logging** for troubleshooting
- **Cleanup procedures** on failure

### Common Issues and Solutions

#### Tests Fail
```bash
# Run tests separately to debug
./scripts/auto_docs.sh test

# Skip tests temporarily
./scripts/auto_docs.sh deploy --skip-tests
```

#### Linting Issues
```bash
# Run with force to override warnings
./scripts/auto_docs.sh deploy --force
```

#### Git Issues
```bash
# Check git status
git status

# Reset if needed
git reset --hard HEAD
```

## 🔒 Security Features

The automation includes several security measures:

- **Path validation** prevents directory traversal attacks
- **File extension filtering** limits file types
- **Pattern blocking** prevents dangerous operations
- **Sandboxed execution** isolates the automation

## 📈 Performance Optimization

### Parallel Processing
- Configurable worker count for parallel operations
- Memory usage monitoring and limits
- Timeout controls for long-running operations

### Caching
- SVG marker caching for map generation
- Documentation build caching
- Git status caching

## 🧪 Testing the Automation

### Dry Run Mode
```bash
# Test without making changes
./scripts/auto_docs.sh deploy --dry-run
```

### Individual Components
```bash
# Test specific components
./scripts/auto_docs.sh docs --dry-run
./scripts/auto_docs.sh wiki --dry-run
./scripts/auto_docs.sh status --dry-run
```

## 🔄 Integration with CI/CD

The automation can be integrated into CI/CD pipelines:

```yaml
# GitHub Actions example
- name: Run Documentation Automation
  run: |
    python scripts/automate_docs_and_deploy.py --skip-tests
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## 📝 Contributing to Automation

### Adding New Features

1. **Extend the main class**: Add new methods to `DocumentationAutomation`
2. **Update configuration**: Add new settings to `automation_config.yaml`
3. **Add tests**: Create tests for new functionality
4. **Update documentation**: Document new features here

### Code Style

- Follow PEP 8 guidelines
- Include comprehensive docstrings
- Add type hints where possible
- Include error handling for all operations

## 🆘 Troubleshooting

### Debug Mode
```bash
# Enable verbose logging
export LOG_LEVEL=DEBUG
./scripts/auto_docs.sh deploy
```

### Manual Steps
If automation fails, you can run steps manually:

1. **Generate docs**: `python -m sphinx.cmd.build -b html docs/source docs/build/html`
2. **Update wikis**: Copy files manually to wiki directories
3. **Git operations**: Use standard git commands
4. **Status update**: Run library commands directly

### Getting Help

- Check the logs in `reports/` directory
- Review the deployment report for details
- Check git status and recent commits
- Verify configuration file syntax

## 📚 Related Documentation

- [Main README](../README.md) - Project overview
- [Testing Guide](../wiki_fresh/Testing-Guide.md) - Testing strategies
- [Getting Started](../wiki_fresh/Getting-Started.md) - Basic setup
- [API Documentation](../docs/build/html/index.html) - Generated API docs

## 🎯 Roadmap

Future enhancements planned:

- [ ] **Multi-language support** for international documentation
- [ ] **Automated translation** using AI services
- [ ] **Advanced reporting** with charts and metrics
- [ ] **Slack/Teams integration** for notifications
- [ ] **Docker containerization** for consistent environments
- [ ] **Cloud deployment** to AWS/GCP/Azure

---

*This automation system is designed to make documentation maintenance effortless and consistent. For questions or issues, please refer to the troubleshooting section or create an issue in the project repository.*
