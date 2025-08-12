# Scripts Directory

This directory contains utility scripts for managing and maintaining the Siege Utilities project.

## Available Scripts

### `sync_to_wiki.py` - Recipe Wiki Synchronization

Automatically syncs recipe documentation from `docs/recipes/` to a GitHub wiki repository.

#### Usage

**Option 1: Sync to existing local wiki repository**
```bash
python scripts/sync_to_wiki.py --wiki-path /path/to/local/wiki/repo
```

**Option 2: Clone and sync to wiki repository**
```bash
python scripts/sync_to_wiki.py --wiki-url https://github.com/username/repo.wiki.git
```

**Option 3: Custom commit message**
```bash
python scripts/sync_to_wiki.py --wiki-path /path/to/wiki --commit-message "Add new analytics recipes"
```

**Option 4: Commit only (don't push)**
```bash
python scripts/sync_to_wiki.py --wiki-path /path/to/wiki --no-push
```

#### What it does

1. **Copies recipes**: Syncs all markdown files from `docs/recipes/` to the wiki
2. **Updates navigation**: Creates/updates wiki index and navigation
3. **Maintains structure**: Preserves directory structure in the wiki
4. **Git integration**: Automatically commits and pushes changes
5. **Cleanup**: Removes temporary files if cloning from URL

#### Prerequisites

- Git installed and configured
- Access to the wiki repository
- Python 3.8+ with standard library modules

### `generate_docstrings.py` - Documentation Generation

Generates docstrings for functions that don't have them.

#### Usage
```bash
python scripts/generate_docstrings.py
```

## GitHub Actions Integration

The `.github/workflows/sync-wiki.yml` workflow automatically syncs recipes to the wiki whenever:

- Changes are pushed to the `main` branch in `docs/recipes/`
- The sync script is modified
- The workflow is manually triggered

### Setting up automatic sync

1. **Enable GitHub Actions** in your repository settings
2. **Create the wiki repository** if it doesn't exist:
   - Go to your repository
   - Click "Wiki" tab
   - Create the first page (this creates the wiki repo)
3. **The workflow will run automatically** on recipe changes

### Manual sync workflow

If you prefer manual control:

1. **Clone the wiki repository**:
   ```bash
   git clone https://github.com/username/repo.wiki.git
   cd repo.wiki
   ```

2. **Run the sync script**:
   ```bash
   python ../scripts/sync_to_wiki.py --wiki-path .
   ```

3. **Push changes**:
   ```bash
   git push origin main
   ```

## Recipe Management Workflow

### Adding new recipes

1. **Create recipe file** in `docs/recipes/` with appropriate category
2. **Follow the recipe template** (see `docs/recipes/README.md`)
3. **Test the recipe** to ensure it works correctly
4. **Commit and push** to main repository
5. **Wiki sync happens automatically** via GitHub Actions

### Updating existing recipes

1. **Edit recipe file** in `docs/recipes/`
2. **Commit and push** changes
3. **Wiki is automatically updated** via GitHub Actions

### Recipe structure

```
docs/recipes/
├── README.md                    # Main recipes index
├── getting_started/            # Beginner recipes
│   ├── basic_setup.md
│   └── first_steps.md
├── file_operations/            # File handling recipes
│   ├── batch_processing.md
│   └── integrity_checking.md
├── distributed_computing/      # Spark/HDFS recipes
│   ├── spark_processing.md
│   └── hdfs_operations.md
└── analytics/                  # Analytics platform recipes
    └── multi_platform_collection.md
```

## Troubleshooting

### Common issues

1. **Wiki sync fails**: Check that the wiki repository exists and is accessible
2. **Permission denied**: Ensure the GitHub Action has write access to the wiki
3. **Merge conflicts**: Resolve conflicts in the wiki repository manually
4. **Script errors**: Check Python version and dependencies

### Manual recovery

If automatic sync fails:

1. **Clone wiki repository manually**
2. **Run sync script locally**
3. **Resolve any conflicts**
4. **Push changes manually**

### Getting help

- Check the [GitHub Actions logs](../../actions) for detailed error information
- Review the [recipe documentation](../docs/recipes/README.md)
- Open an issue in the main repository

## Contributing

To add new scripts:

1. **Create script file** in this directory
2. **Add usage documentation** in this README
3. **Include error handling** and logging
4. **Test thoroughly** before committing
5. **Update this README** with usage instructions

## Security Notes

- **Never commit sensitive information** (API keys, passwords, etc.)
- **Use environment variables** for configuration
- **Validate inputs** to prevent injection attacks
- **Limit script permissions** to minimum required access
