#!/bin/bash
# Complete Overnight Testing and Recommendations Pipeline
# This script runs the full testing suite and generates morning recommendations

echo "Starting Complete Overnight Testing Pipeline..."
echo "=============================================="

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

# Step 1: Run comprehensive function testing
echo "Step 1: Running comprehensive function testing..."
python overnight_testing_suite.py

if [ $? -ne 0 ]; then
    echo "Error: Function testing failed!"
    exit 1
fi

echo "Function testing completed successfully!"

# Step 2: Generate morning recommendations
echo ""
echo "Step 2: Generating morning recommendations..."
python morning_recommendations_generator.py

if [ $? -ne 0 ]; then
    echo "Error: Recommendations generation failed!"
    exit 1
fi

echo "Recommendations generation completed successfully!"

# Step 3: Display summary
echo ""
echo "=============================================="
echo "Overnight Pipeline Completed Successfully!"
echo ""
echo "Generated files:"
echo "- overnight_test_results.json (detailed test results)"
echo "- overnight_test_report.md (human-readable test report)"
echo "- function_validation_log.txt (execution log)"
echo "- morning_recommendations.md (prioritized action items)"
echo "- function_priority_list.json (functions ranked by priority)"
echo ""
echo "Review morning_recommendations.md for tomorrow's priorities!"
echo "=============================================="
