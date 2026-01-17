#!/usr/bin/env python3
"""
Comprehensive Morning Report Generator

This script generates a detailed morning report based on all overnight testing results.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

def generate_comprehensive_morning_report():
    """Generate a comprehensive morning report from all test results."""
    
    print("📊 Generating Comprehensive Morning Report")
    print("=" * 50)
    
    # Load all test results
    results_dir = Path("overnight_results")
    if not results_dir.exists():
        print("❌ No overnight results directory found")
        return
    
    # Load all result files
    all_results = {}
    
    result_files = [
        "overnight_test_results.json",
        "critical_functions_test_results.json", 
        "notebook_conversion_results.json",
        "recipe_test_results.json"
    ]
    
    for result_file in result_files:
        file_path = results_dir / result_file
        if file_path.exists():
            try:
                with open(file_path, 'r') as f:
                    all_results[result_file] = json.load(f)
                print(f"✅ Loaded: {result_file}")
            except Exception as e:
                print(f"❌ Error loading {result_file}: {e}")
        else:
            print(f"⚠️  Not found: {result_file}")
    
    # Generate comprehensive report
    report_path = results_dir / "comprehensive_morning_report.md"
    
    with open(report_path, 'w') as f:
        f.write("# 🌅 Comprehensive Morning Report\n\n")
        f.write(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Executive Summary
        f.write("## 📊 Executive Summary\n\n")
        executive_summary = generate_executive_summary(all_results)
        f.write(executive_summary)
        f.write("\n")
        
        # Function Testing Results
        f.write("## 🔬 Function Testing Results\n\n")
        function_results = generate_function_testing_section(all_results)
        f.write(function_results)
        f.write("\n")
        
        # Notebook Testing Results
        f.write("## 📓 Notebook Testing Results\n\n")
        notebook_results = generate_notebook_testing_section(all_results)
        f.write(notebook_results)
        f.write("\n")
        
        # Recipe Testing Results
        f.write("## 📚 Recipe Testing Results\n\n")
        recipe_results = generate_recipe_testing_section(all_results)
        f.write(recipe_results)
        f.write("\n")
        
        # Critical Issues
        f.write("## 🚨 Critical Issues\n\n")
        critical_issues = generate_critical_issues_section(all_results)
        f.write(critical_issues)
        f.write("\n")
        
        # Recommendations
        f.write("## 🎯 Recommendations\n\n")
        recommendations = generate_recommendations_section(all_results)
        f.write(recommendations)
        f.write("\n")
        
        # Next Steps
        f.write("## 🚀 Next Steps\n\n")
        next_steps = generate_next_steps_section(all_results)
        f.write(next_steps)
        f.write("\n")
    
    print(f"✅ Comprehensive morning report generated: {report_path}")
    
    # Also generate a JSON summary for programmatic access
    summary_path = results_dir / "morning_report_summary.json"
    summary_data = {
        "generated_at": datetime.now().isoformat(),
        "executive_summary": extract_summary_metrics(all_results),
        "key_findings": extract_key_findings(all_results),
        "recommendations": extract_recommendations(all_results)
    }
    
    with open(summary_path, 'w') as f:
        json.dump(summary_data, f, indent=2)
    
    print(f"✅ Summary data saved: {summary_path}")

def generate_executive_summary(all_results: Dict[str, Any]) -> str:
    """Generate executive summary section."""
    
    summary = []
    
    # Calculate overall metrics
    total_tests = 0
    successful_tests = 0
    total_functions = 0
    working_functions = 0
    
    # Process each result file
    for result_file, results in all_results.items():
        if "summary" in results:
            summary_data = results["summary"]
            total_tests += summary_data.get("total_tests", 0)
            successful_tests += summary_data.get("successful_tests", 0)
        
        if "tests" in results:
            for module, module_results in results["tests"].items():
                if isinstance(module_results, dict):
                    total_functions += len(module_results)
                    working_functions += sum(1 for r in module_results.values() if r.get("success", False))
    
    success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
    function_success_rate = (working_functions / total_functions * 100) if total_functions > 0 else 0
    
    summary.append(f"### 🎯 Overall Performance")
    summary.append(f"- **Total Tests Executed**: {total_tests}")
    summary.append(f"- **Successful Tests**: {successful_tests}")
    summary.append(f"- **Overall Success Rate**: {success_rate:.1f}%")
    summary.append(f"- **Functions Tested**: {total_functions}")
    summary.append(f"- **Working Functions**: {working_functions}")
    summary.append(f"- **Function Success Rate**: {function_success_rate:.1f}%")
    summary.append("")
    
    # Key achievements
    summary.append("### 🏆 Key Achievements")
    if success_rate >= 80:
        summary.append("- ✅ **Excellent Success Rate**: Most tests passed successfully")
    elif success_rate >= 60:
        summary.append("- 🟡 **Good Success Rate**: Majority of tests passed")
    else:
        summary.append("- 🔴 **Needs Improvement**: Many tests failed")
    
    if function_success_rate >= 70:
        summary.append("- ✅ **Strong Function Coverage**: Most functions are working")
    elif function_success_rate >= 50:
        summary.append("- 🟡 **Moderate Function Coverage**: About half of functions working")
    else:
        summary.append("- 🔴 **Limited Function Coverage**: Many functions need work")
    
    summary.append("")
    
    return "\n".join(summary)

def generate_function_testing_section(all_results: Dict[str, Any]) -> str:
    """Generate function testing results section."""
    
    section = []
    
    # Process critical functions test results
    if "critical_functions_test_results.json" in all_results:
        critical_results = all_results["critical_functions_test_results.json"]
        
        section.append("### 🔬 Critical Functions Testing")
        
        if "summary" in critical_results:
            summary = critical_results["summary"]
            section.append(f"- **Total Critical Functions Tested**: {summary.get('total_tests', 0)}")
            section.append(f"- **Successful**: {summary.get('successful_tests', 0)}")
            section.append(f"- **Failed**: {summary.get('failed_tests', 0)}")
            section.append(f"- **Success Rate**: {summary.get('success_rate', 0):.1f}%")
            section.append("")
        
        if "tests" in critical_results:
            section.append("#### Module Breakdown:")
            for module, module_results in critical_results["tests"].items():
                if isinstance(module_results, dict):
                    module_success = sum(1 for r in module_results.values() if r.get("success", False))
                    module_total = len(module_results)
                    module_rate = (module_success / module_total * 100) if module_total > 0 else 0
                    
                    status_icon = "✅" if module_rate >= 70 else "🟡" if module_rate >= 40 else "❌"
                    section.append(f"- {status_icon} **{module.upper()}**: {module_success}/{module_total} ({module_rate:.1f}%)")
            
            section.append("")
    
    return "\n".join(section)

def generate_notebook_testing_section(all_results: Dict[str, Any]) -> str:
    """Generate notebook testing results section."""
    
    section = []
    
    if "notebook_conversion_results.json" in all_results:
        notebook_results = all_results["notebook_conversion_results.json"]
        
        section.append("### 📓 Notebook Conversion & Testing")
        
        # Count successful conversions
        conversions = notebook_results.get("conversions", {})
        successful_conversions = sum(1 for r in conversions.values() if r.get("success", False))
        total_notebooks = len(conversions)
        
        section.append(f"- **Total Notebooks**: {total_notebooks}")
        section.append(f"- **Successfully Converted**: {successful_conversions}")
        section.append(f"- **Conversion Success Rate**: {(successful_conversions/total_notebooks*100):.1f}%")
        section.append("")
        
        # Test results
        tests = notebook_results.get("tests", {})
        if tests:
            successful_tests = sum(1 for r in tests.values() if r.get("success", False))
            total_tests = len(tests)
            section.append(f"- **Total Tests Executed**: {total_tests}")
            section.append(f"- **Successful Tests**: {successful_tests}")
            section.append(f"- **Test Success Rate**: {(successful_tests/total_tests*100):.1f}%")
            section.append("")
    
    return "\n".join(section)

def generate_recipe_testing_section(all_results: Dict[str, Any]) -> str:
    """Generate recipe testing results section."""
    
    section = []
    
    if "recipe_test_results.json" in all_results:
        recipe_results = all_results["recipe_test_results.json"]
        
        section.append("### 📚 Recipe Code Testing")
        
        # Count recipes processed
        recipes = recipe_results.get("recipes", {})
        successful_recipes = sum(1 for r in recipes.values() if r.get("success", False))
        total_recipes = len(recipes)
        
        section.append(f"- **Total Recipes**: {total_recipes}")
        section.append(f"- **Successfully Processed**: {successful_recipes}")
        section.append(f"- **Processing Success Rate**: {(successful_recipes/total_recipes*100):.1f}%")
        section.append("")
        
        # Code blocks found
        code_blocks = recipe_results.get("code_blocks", {})
        total_code_blocks = sum(len(blocks) for blocks in code_blocks.values())
        section.append(f"- **Total Code Blocks Found**: {total_code_blocks}")
        section.append("")
        
        # Test results
        tests = recipe_results.get("tests", {})
        if tests:
            successful_tests = sum(1 for r in tests.values() if r.get("success", False))
            total_tests = len(tests)
            section.append(f"- **Total Tests Executed**: {total_tests}")
            section.append(f"- **Successful Tests**: {successful_tests}")
            section.append(f"- **Test Success Rate**: {(successful_tests/total_tests*100):.1f}%")
            section.append("")
    
    return "\n".join(section)

def generate_critical_issues_section(all_results: Dict[str, Any]) -> str:
    """Generate critical issues section."""
    
    section = []
    
    # Collect all errors
    all_errors = []
    for result_file, results in all_results.items():
        if "errors" in results:
            for error in results["errors"]:
                all_errors.append({
                    "source": result_file,
                    "error": error
                })
    
    if not all_errors:
        section.append("✅ **No Critical Issues Found**")
        section.append("")
        section.append("All tests completed without critical errors.")
        section.append("")
        return "\n".join(section)
    
    section.append(f"🚨 **{len(all_errors)} Critical Issues Identified**")
    section.append("")
    
    # Group errors by type
    error_types = {}
    for error_data in all_errors:
        error = error_data["error"]
        error_type = error.get("type", "unknown")
        if error_type not in error_types:
            error_types[error_type] = []
        error_types[error_type].append(error_data)
    
    for error_type, errors in error_types.items():
        section.append(f"#### {error_type.replace('_', ' ').title()}")
        section.append(f"- **Count**: {len(errors)}")
        
        # Show first few errors as examples
        for i, error_data in enumerate(errors[:3]):
            error = error_data["error"]
            section.append(f"- **Example {i+1}**: {error.get('error', 'Unknown error')[:100]}...")
        
        if len(errors) > 3:
            section.append(f"- ... and {len(errors) - 3} more")
        
        section.append("")
    
    return "\n".join(section)

def generate_recommendations_section(all_results: Dict[str, Any]) -> str:
    """Generate recommendations section."""
    
    section = []
    
    # Analyze results to generate recommendations
    total_tests = 0
    successful_tests = 0
    
    for result_file, results in all_results.items():
        if "summary" in results:
            summary = results["summary"]
            total_tests += summary.get("total_tests", 0)
            successful_tests += summary.get("successful_tests", 0)
    
    success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
    
    section.append("### 🎯 Immediate Actions")
    
    if success_rate < 50:
        section.append("- 🔴 **High Priority**: Focus on fixing critical failures first")
        section.append("- 🔴 **Review Error Logs**: Analyze error patterns and fix root causes")
        section.append("- 🔴 **Simplify Tests**: Start with basic functionality before complex scenarios")
    elif success_rate < 80:
        section.append("- 🟡 **Medium Priority**: Address failing tests systematically")
        section.append("- 🟡 **Improve Test Coverage**: Add more comprehensive test cases")
        section.append("- 🟡 **Document Issues**: Create tickets for persistent problems")
    else:
        section.append("- ✅ **Excellent Progress**: Continue with planned improvements")
        section.append("- ✅ **Expand Testing**: Add more edge cases and integration tests")
        section.append("- ✅ **Document Success**: Update documentation for working functions")
    
    section.append("")
    
    section.append("### 📋 Systematic Improvements")
    section.append("1. **Fix Critical Functions**: Address functions with high failure rates")
    section.append("2. **Update Documentation**: Ensure all working functions are documented")
    section.append("3. **Create Unit Tests**: Add formal unit tests for validated functions")
    section.append("4. **Improve Error Handling**: Add better error messages and recovery")
    section.append("5. **Performance Optimization**: Optimize functions that are working but slow")
    section.append("")
    
    section.append("### 🚀 Long-term Goals")
    section.append("- **Complete Function Coverage**: Test all 260+ functions in the library")
    section.append("- **Production Readiness**: Ensure all functions are production-ready")
    section.append("- **Documentation Completeness**: Update all wiki pages and recipes")
    section.append("- **Automated Testing**: Set up continuous testing pipeline")
    section.append("")
    
    return "\n".join(section)

def generate_next_steps_section(all_results: Dict[str, Any]) -> str:
    """Generate next steps section."""
    
    section = []
    
    section.append("### 📅 Today's Priority Tasks")
    section.append("1. **Review Failed Tests**: Analyze and fix the most critical failures")
    section.append("2. **Update Function Status**: Mark functions as tested in status tracking")
    section.append("3. **Create Unit Tests**: Add formal tests for newly validated functions")
    section.append("4. **Document Working Functions**: Update documentation for successful tests")
    section.append("")
    
    section.append("### 🔄 Ongoing Maintenance")
    section.append("- **Daily Testing**: Run overnight tests regularly to catch regressions")
    section.append("- **Function Status Updates**: Keep function status tracking current")
    section.append("- **Error Monitoring**: Track and resolve recurring issues")
    section.append("- **Performance Monitoring**: Watch for performance degradation")
    section.append("")
    
    section.append("### 📈 Success Metrics to Track")
    section.append("- **Function Success Rate**: Target 90%+ working functions")
    section.append("- **Test Coverage**: Target 95%+ function coverage")
    section.append("- **Documentation Coverage**: Target 100% documented functions")
    section.append("- **Error Rate**: Target <5% test failure rate")
    section.append("")
    
    return "\n".join(section)

def extract_summary_metrics(all_results: Dict[str, Any]) -> Dict[str, Any]:
    """Extract summary metrics for JSON output."""
    
    total_tests = 0
    successful_tests = 0
    total_functions = 0
    working_functions = 0
    
    for result_file, results in all_results.items():
        if "summary" in results:
            summary = results["summary"]
            total_tests += summary.get("total_tests", 0)
            successful_tests += summary.get("successful_tests", 0)
        
        if "tests" in results:
            for module, module_results in results["tests"].items():
                if isinstance(module_results, dict):
                    total_functions += len(module_results)
                    working_functions += sum(1 for r in module_results.values() if r.get("success", False))
    
    return {
        "total_tests": total_tests,
        "successful_tests": successful_tests,
        "success_rate": (successful_tests / total_tests * 100) if total_tests > 0 else 0,
        "total_functions": total_functions,
        "working_functions": working_functions,
        "function_success_rate": (working_functions / total_functions * 100) if total_functions > 0 else 0
    }

def extract_key_findings(all_results: Dict[str, Any]) -> List[str]:
    """Extract key findings from test results."""
    
    findings = []
    
    # Calculate overall success rate
    total_tests = 0
    successful_tests = 0
    
    for result_file, results in all_results.items():
        if "summary" in results:
            summary = results["summary"]
            total_tests += summary.get("total_tests", 0)
            successful_tests += summary.get("successful_tests", 0)
    
    success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
    
    if success_rate >= 80:
        findings.append("Excellent overall test success rate")
    elif success_rate >= 60:
        findings.append("Good overall test success rate")
    else:
        findings.append("Low overall test success rate - needs attention")
    
    # Check for specific module performance
    if "critical_functions_test_results.json" in all_results:
        critical_results = all_results["critical_functions_test_results.json"]
        if "tests" in critical_results:
            for module, module_results in critical_results["tests"].items():
                if isinstance(module_results, dict):
                    module_success = sum(1 for r in module_results.values() if r.get("success", False))
                    module_total = len(module_results)
                    module_rate = (module_success / module_total * 100) if module_total > 0 else 0
                    
                    if module_rate >= 80:
                        findings.append(f"{module.upper()} module performing excellently")
                    elif module_rate >= 50:
                        findings.append(f"{module.upper()} module performing moderately")
                    else:
                        findings.append(f"{module.upper()} module needs significant work")
    
    return findings

def extract_recommendations(all_results: Dict[str, Any]) -> List[str]:
    """Extract recommendations from test results."""
    
    recommendations = []
    
    # Analyze error patterns
    all_errors = []
    for result_file, results in all_results.items():
        if "errors" in results:
            all_errors.extend(results["errors"])
    
    if len(all_errors) > 10:
        recommendations.append("High error count - focus on fixing critical issues first")
    elif len(all_errors) > 5:
        recommendations.append("Moderate error count - address systematically")
    else:
        recommendations.append("Low error count - continue with planned improvements")
    
    # Check for specific issues
    error_types = {}
    for error in all_errors:
        error_type = error.get("type", "unknown")
        error_types[error_type] = error_types.get(error_type, 0) + 1
    
    for error_type, count in error_types.items():
        if count > 3:
            recommendations.append(f"Multiple {error_type} errors - investigate root cause")
    
    return recommendations

def main():
    """Main entry point."""
    print("🌅 Comprehensive Morning Report Generator")
    print("Generating detailed report from all overnight test results")
    print()
    
    generate_comprehensive_morning_report()
    
    print("\n✅ Comprehensive morning report generated!")
    print("Check overnight_results/comprehensive_morning_report.md for details")

if __name__ == "__main__":
    main()
