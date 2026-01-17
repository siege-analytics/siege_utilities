#!/usr/bin/env python3
"""
Morning Recommendations Generator
================================

This script analyzes the overnight test results and generates actionable
recommendations for the next day's work.

Usage:
    python morning_recommendations_generator.py

Output:
    - morning_recommendations.md: Prioritized action items
    - function_priority_list.json: Functions ranked by priority
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

def load_overnight_results() -> Dict[str, Any]:
    """Load the overnight test results."""
    results_file = Path('overnight_test_results.json')
    
    if not results_file.exists():
        print("Error: overnight_test_results.json not found!")
        print("Run the overnight testing suite first.")
        sys.exit(1)
        
    with open(results_file, 'r') as f:
        return json.load(f)

def analyze_function_health(results: Dict[str, Any]) -> Dict[str, List[str]]:
    """Analyze function health and categorize issues."""
    health_analysis = {
        'critical_issues': [],
        'high_priority_fixes': [],
        'medium_priority_improvements': [],
        'low_priority_enhancements': [],
        'well_functioning': []
    }
    
    for func_name, result in results['function_results'].items():
        status = result['overall_status']
        import_test = result['import_test']
        execution_test = result['execution_test']
        
        # Categorize based on status and issues
        if status == 'broken':
            health_analysis['critical_issues'].append(func_name)
        elif status == 'failed':
            health_analysis['high_priority_fixes'].append(func_name)
        elif status == 'skipped':
            health_analysis['medium_priority_improvements'].append(func_name)
        elif status == 'working':
            # Check for improvement opportunities
            issues = []
            if not import_test['has_docstring']:
                issues.append('missing_docstring')
            if not import_test['has_type_hints']:
                issues.append('missing_type_hints')
            if import_test['execution_time'] > 0.1:
                issues.append('slow_execution')
                
            if issues:
                health_analysis['low_priority_enhancements'].append({
                    'function': func_name,
                    'issues': issues
                })
            else:
                health_analysis['well_functioning'].append(func_name)
    
    return health_analysis

def generate_priority_actions(health_analysis: Dict[str, List[str]], results: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate prioritized action items."""
    actions = []
    
    # Critical issues - must fix immediately
    if health_analysis['critical_issues']:
        actions.append({
            'priority': 1,
            'category': 'critical',
            'title': 'Fix Critical Import/Execution Failures',
            'description': f"Fix {len(health_analysis['critical_issues'])} functions that completely fail to import or execute",
            'functions': health_analysis['critical_issues'][:10],  # Limit to first 10
            'estimated_time': '2-4 hours',
            'impact': 'High - prevents basic library functionality'
        })
    
    # High priority fixes
    if health_analysis['high_priority_fixes']:
        actions.append({
            'priority': 2,
            'category': 'high',
            'title': 'Fix Function Execution Issues',
            'description': f"Fix {len(health_analysis['high_priority_fixes'])} functions that fail during execution",
            'functions': health_analysis['high_priority_fixes'][:10],
            'estimated_time': '1-3 hours',
            'impact': 'High - affects user experience'
        })
    
    # Medium priority improvements
    if health_analysis['medium_priority_improvements']:
        actions.append({
            'priority': 3,
            'category': 'medium',
            'title': 'Enable Skipped Functions',
            'description': f"Enable {len(health_analysis['medium_priority_improvements'])} functions that were skipped due to missing dependencies",
            'functions': health_analysis['medium_priority_improvements'][:10],
            'estimated_time': '2-6 hours',
            'impact': 'Medium - expands library capabilities'
        })
    
    # Documentation improvements
    docstring_issues = [func for func in results['function_results'].values() 
                       if not func['import_test']['has_docstring']]
    if docstring_issues:
        actions.append({
            'priority': 4,
            'category': 'documentation',
            'title': 'Add Missing Docstrings',
            'description': f"Add docstrings to {len(docstring_issues)} functions",
            'functions': [name for name, result in results['function_results'].items() 
                         if not result['import_test']['has_docstring']][:10],
            'estimated_time': '3-5 hours',
            'impact': 'Medium - improves developer experience'
        })
    
    # Type hints improvements
    type_hint_issues = [func for func in results['function_results'].values() 
                       if not func['import_test']['has_type_hints']]
    if type_hint_issues:
        actions.append({
            'priority': 5,
            'category': 'type_hints',
            'title': 'Add Missing Type Hints',
            'description': f"Add type hints to {len(type_hint_issues)} functions",
            'functions': [name for name, result in results['function_results'].items() 
                         if not result['import_test']['has_type_hints']][:10],
            'estimated_time': '2-4 hours',
            'impact': 'Low - improves code quality'
        })
    
    return actions

def generate_morning_report(actions: List[Dict[str, Any]], health_analysis: Dict[str, List[str]], results: Dict[str, Any]) -> str:
    """Generate the morning recommendations report."""
    report = f"""# Morning Recommendations - {datetime.now().strftime('%Y-%m-%d')}

## Executive Summary

Based on overnight testing of {results['total_functions']} functions:

- **Critical Issues**: {len(health_analysis['critical_issues'])} functions need immediate attention
- **High Priority Fixes**: {len(health_analysis['high_priority_fixes'])} functions need execution fixes
- **Medium Priority**: {len(health_analysis['medium_priority_improvements'])} functions need dependency work
- **Well Functioning**: {len(health_analysis['well_functioning'])} functions are working well

## Prioritized Action Items

"""
    
    for action in actions:
        report += f"""### {action['priority']}. {action['title']}

**Priority**: {action['category'].upper()}  
**Estimated Time**: {action['estimated_time']}  
**Impact**: {action['impact']}

**Description**: {action['description']}

**Functions to Address**:
"""
        for func in action['functions'][:5]:  # Show first 5
            if isinstance(func, dict):
                report += f"- {func['function']} (issues: {', '.join(func['issues'])})"
            else:
                report += f"- {func}"
        report += "\n\n"
    
    # Add module-specific recommendations
    report += "## Module-Specific Recommendations\n\n"
    
    for module, summary in results['module_summary'].items():
        if not summary['importable']:
            report += f"### {module} - CRITICAL\n"
            report += f"- **Issue**: Module not importable\n"
            report += f"- **Error**: {summary['error']}\n"
            report += f"- **Action**: Fix import issues immediately\n\n"
        elif summary['function_count'] == 0:
            report += f"### {module} - WARNING\n"
            report += f"- **Issue**: No functions found\n"
            report += f"- **Action**: Verify module structure\n\n"
    
    # Add performance notes
    slow_functions = [name for name, result in results['function_results'].items() 
                     if result['import_test']['execution_time'] > 0.1]
    
    if slow_functions:
        report += "## Performance Notes\n\n"
        report += f"**Slow Functions** ({len(slow_functions)} total):\n"
        for func in slow_functions[:5]:
            report += f"- {func}\n"
        report += "\n"
    
    # Add testing recommendations
    report += "## Testing Recommendations\n\n"
    report += "1. **Start with Critical Issues**: Fix import/execution failures first\n"
    report += "2. **Use Mini-Projects**: Test functions in real-world scenarios\n"
    report += "3. **Documentation First**: Add docstrings before type hints\n"
    report += "4. **Incremental Testing**: Test fixes immediately after implementation\n"
    report += "5. **User Feedback**: Test with actual use cases, not just unit tests\n\n"
    
    return report

def main():
    """Main execution function."""
    print("Generating Morning Recommendations...")
    print("=" * 50)
    
    # Load overnight results
    results = load_overnight_results()
    
    # Analyze function health
    health_analysis = analyze_function_health(results)
    
    # Generate priority actions
    actions = generate_priority_actions(health_analysis, results)
    
    # Generate morning report
    report = generate_morning_report(actions, health_analysis, results)
    
    # Save report
    with open('morning_recommendations.md', 'w') as f:
        f.write(report)
    
    # Save priority list
    priority_data = {
        'timestamp': datetime.now().isoformat(),
        'actions': actions,
        'health_analysis': health_analysis
    }
    
    with open('function_priority_list.json', 'w') as f:
        json.dump(priority_data, f, indent=2)
    
    print("Morning recommendations generated!")
    print("Files created:")
    print("- morning_recommendations.md")
    print("- function_priority_list.json")
    
    # Print summary
    print(f"\nSummary:")
    print(f"- Critical issues: {len(health_analysis['critical_issues'])}")
    print(f"- High priority fixes: {len(health_analysis['high_priority_fixes'])}")
    print(f"- Medium priority improvements: {len(health_analysis['medium_priority_improvements'])}")
    print(f"- Well functioning: {len(health_analysis['well_functioning'])}")

if __name__ == "__main__":
    main()
