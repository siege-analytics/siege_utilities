# Siege Utilities Test Suite

This comprehensive test suite is designed to **smoke out broken functions** and identify issues in the siege-utilities library. The tests are specifically crafted to expose bugs, edge cases, and implementation problems.

## 🎯 Test Objectives

1. **Smoke Testing**: Quickly identify broken functions
2. **Edge Case Testing**: Test boundary conditions and unusual inputs
3. **Error Handling**: Verify graceful failure handling
4. **Integration Testing**: Test function interdependencies
5. **Performance Testing**: Identify slow or problematic operations

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r test_requirements.txt
```

### 2. Run Quick Smoke Test

```bash
python run_tests.py
```

This runs a basic smoke test to verify the package imports and core functions work.

### 3. Run Full Test Suite

```bash
python run_tests.py --mode all
```

## 🔥 Test Modes

### Smoke Tests (Recommended First)
```bash
python run_tests.py --mode smoke
```
- **Purpose**: Quickly find broken functions
- **Duration**: ~30 seconds
- **Stops after**: 10 failures
- **Best for**: Initial assessment

### Fast Tests
```bash
python run_tests.py --mode fast
```
- **Purpose**: Skip slow tests, focus on core functionality
- **Duration**: ~2 minutes
- **Excludes**: Network tests, large file operations

### Coverage Analysis
```bash
python run_tests.py --mode coverage
```
- **Purpose**: Generate code coverage report
- **Duration**: ~10 minutes
- **Output**: HTML coverage report in `htmlcov/`

## 🐛 Expected Failures

These tests are **designed to find bugs**. Here are some issues you should expect to see:

### File Operations Issues
1. **Row Counting Functions**: 
   - `count_total_rows_in_file_pythonically()` - **BUG**: Uses filename in loop instead of file handle
   - `count_empty_rows_in_file_pythonically()` - **BUG**: Same issue as above

2. **Shell Operations**:
   - Missing import for `io` module in `remove_empty_rows_in_file_using_sed()`
   - Undefined variables in error handling paths

### Distributed Computing Issues
1. **Spark Utils**:
   - `move_column_to_front_of_dataframe()` - **BUG**: Returns original DataFrame instead of reordered one
   - Multiple functions use undefined variables like `RESULTS_OUTPUT_FORMAT`
   - Easter egg: `reproject_geom_columns()` prints "I LOVE LEENA"

## 📊 Setup Instructions

1. **Create test directory structure**:
```bash
mkdir tests
mkdir reports
```

2. **Copy all test files** from this artifact to appropriate locations

3. **Install dependencies**:
```bash
pip install -r test_requirements.txt
```

4. **Run smoke tests**:
```bash
python run_tests.py --mode smoke
```

## 💡 Tips for Success

1. **Start with Smoke Tests**: Always run smoke tests first
2. **Fix High-Impact Issues**: Focus on functions that completely fail
3. **Test After Each Fix**: Re-run tests after making changes
4. **Use Verbose Mode**: When debugging specific issues
5. **Check Dependencies**: Some tests require optional packages
