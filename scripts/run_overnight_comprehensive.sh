#!/bin/bash
# ================================================================
# Siege Utilities - Comprehensive Battle Testing Script
# ================================================================
# This script runs comprehensive tests and generates reports.
# Used by CI/CD pipeline and can be run locally for thorough testing.
# ================================================================

set -e
set -o pipefail

# Get script directory (portable, no hardcoded paths)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

# Keep reports in $REPO_ROOT/overnight_results/ regardless of the caller's
# working directory, matching the CI artifact upload path.
mkdir -p overnight_results

echo "=========================================="
echo "Siege Utilities - Battle Test Suite"
echo "Started: $(date)"
echo "=========================================="

# Run comprehensive pytest with extended output
echo ""
echo "Running comprehensive test suite..."
echo ""

# Allow pytest to fail so we can capture its status and still write the summary.
set +e
# Use uv if available (CI), fall back to python directly
if command -v uv &> /dev/null; then
    uv run pytest tests/ \
        -v \
        --tb=short \
        --durations=20 \
        -m "not integration and not postgis" \
        --ignore=tests/test_notebooks.py \
        --cov=siege_utilities \
        --cov-report=term-missing \
        --cov-report=html:overnight_results/coverage_html \
        --cov-report=json:overnight_results/coverage.json \
        2>&1 | tee overnight_results/test_output.txt
    PIPE_STATUS=("${PIPESTATUS[@]}")
else
    python -m pytest tests/ \
        -v \
        --tb=short \
        --durations=20 \
        -m "not integration and not postgis" \
        --ignore=tests/test_notebooks.py \
        --cov=siege_utilities \
        --cov-report=term-missing \
        --cov-report=html:overnight_results/coverage_html \
        --cov-report=json:overnight_results/coverage.json \
        2>&1 | tee overnight_results/test_output.txt
    PIPE_STATUS=("${PIPESTATUS[@]}")
fi
set -e

# Both pipeline stages count: a pytest pass is not a result unless its output
# artifact was actually written.
PYTEST_EXIT_CODE=${PIPE_STATUS[0]}
TEE_EXIT_CODE=${PIPE_STATUS[1]}
TEST_EXIT_CODE=$PYTEST_EXIT_CODE
OUTPUT_ARTIFACT="written"
if [[ "$TEE_EXIT_CODE" -ne 0 || ! -f overnight_results/test_output.txt ]]; then
    OUTPUT_ARTIFACT="absent"
    echo "ERROR: could not write overnight_results/test_output.txt (tee exit $TEE_EXIT_CODE)." >&2
    if [[ "$TEST_EXIT_CODE" -eq 0 ]]; then
        TEST_EXIT_CODE=1
    fi
fi

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
    "pytest_exit_code": $PYTEST_EXIT_CODE,
    "tee_exit_code": $TEE_EXIT_CODE,
    "output_artifact": "$OUTPUT_ARTIFACT",
    "script_dir": "$SCRIPT_DIR",
    "python_version": "$(python --version 2>&1)"
}
EOF

echo ""
echo "Results saved to: $REPO_ROOT/overnight_results/"
echo "=========================================="

exit $TEST_EXIT_CODE
