# Purgatory Directory

This directory contains files that have been moved from the main repository but are preserved for reference or potential future use.

## 📁 Directory Structure

### `temporary_files/`
Contains temporary diagnostic and utility scripts that were used during development:
- `check_imports.py` - Import diagnostic script
- `diagnose_pyspark.py` - PySpark diagnostic script
- `find_test_returns.py` - Test analysis script
- `create_notebook.py` - Notebook creation script
- `run_tests.py` - Redundant test runner script

### `historical_docs/`
Contains historical documentation and reports:
- `ANALYSIS_REPORT.md` - Historical analysis report (outdated)
- `RESTORATION_COMPLETE.md` - Historical restoration report (outdated)
- `archive/` - Old wiki versions and archived content

### `redundant_docs/`
Contains redundant documentation that has been superseded:
- `docs/` - Sphinx documentation (redundant with wiki)

### `example_files/`
Contains example files and projects:
- `examples/` - Example notebooks and demos
- `projects/` - Example project structures

### `outdated_scripts/`
Contains outdated or redundant scripts:
- Various shell scripts and automation tools
- Scripts that have been superseded by modern alternatives

## 🔄 Restoration

If you need to restore any files from purgatory:

```bash
# Restore a specific file
cp purgatory/temporary_files/check_imports.py ./

# Restore an entire directory
cp -r purgatory/example_files/examples ./

# Restore all files (not recommended)
cp -r purgatory/* ./
```

## ⚠️ Important Notes

- Files in purgatory are **not** part of the active codebase
- They are preserved for reference and potential future use
- Some files may be outdated or incompatible with current versions
- Always review files before restoring them to the main directory

## 🧹 Cleanup

This directory can be safely deleted if you're certain the files are no longer needed:

```bash
# Remove entire purgatory directory
rm -rf purgatory/
```

**Note**: This action is irreversible. Make sure you don't need any of these files before deletion.
