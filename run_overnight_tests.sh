#!/bin/bash
# Overnight Testing Runner for siege_utilities
# This script runs the comprehensive testing suite and generates reports

echo "Starting Overnight Testing Suite for siege_utilities..."
echo "=================================================="

# Change to the correct directory
cd "$(dirname "$0")"

# Activate the virtual environment if it exists
if [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
elif [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Run the testing suite
echo "Running comprehensive function testing..."
python overnight_testing_suite.py

# Check if the test completed successfully
if [ $? -eq 0 ]; then
    echo ""
    echo "=================================================="
    echo "Overnight testing completed successfully!"
    echo ""
    echo "Generated files:"
    echo "- overnight_test_results.json (detailed results)"
    echo "- overnight_test_report.md (human-readable report)"
    echo "- function_validation_log.txt (execution log)"
    echo ""
    echo "Review these files in the morning for recommendations."
else
    echo ""
    echo "=================================================="
    echo "Overnight testing failed!"
    echo "Check function_validation_log.txt for details."
    exit 1
fi
