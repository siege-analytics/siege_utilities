#!/bin/bash
# ================================================================
# Siege Utilities - Comprehensive Battle Testing Script
# ================================================================
# This script runs comprehensive tests and generates reports.
# Used by CI/CD pipeline and can be run locally for thorough testing.
# ================================================================

set -e

# Get script directory (portable, no hardcoded paths)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Create output directory
mkdir -p overnight_results

echo "=========================================="
echo "Siege Utilities - Battle Test Suite"
echo "Started: $(date)"
echo "=========================================="

# Run comprehensive pytest with extended output
echo ""
echo "Running comprehensive test suite..."
echo ""

# Use uv if available (CI), fall back to python directly
if command -v uv &> /dev/null; then
    uv run pytest tests/ \
        -v \
        --tb=short \
        --durations=20 \
        --cov=siege_utilities \
        --cov-report=term-missing \
        --cov-report=html:overnight_results/coverage_html \
        --cov-report=json:overnight_results/coverage.json \
        2>&1 | tee overnight_results/test_output.txt
else
    python -m pytest tests/ \
        -v \
        --tb=short \
        --durations=20 \
        --cov=siege_utilities \
        --cov-report=term-missing \
        --cov-report=html:overnight_results/coverage_html \
        --cov-report=json:overnight_results/coverage.json \
        2>&1 | tee overnight_results/test_output.txt
fi

TEST_EXIT_CODE=$?

# Generate summary
echo ""
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo "Exit Code: $TEST_EXIT_CODE"
echo "Completed: $(date)"

# Create summary JSON
cat > overnight_results/summary.json << EOF
{
    "timestamp": "$(date -Iseconds)",
    "exit_code": $TEST_EXIT_CODE,
    "script_dir": "$SCRIPT_DIR",
    "python_version": "$(python --version 2>&1)"
}
EOF

echo ""
echo "Results saved to: overnight_results/"
echo "=========================================="

exit $TEST_EXIT_CODE
