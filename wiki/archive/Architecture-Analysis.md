# Architecture Analysis - Package Structure and Code Analysis

## Problem

You need to understand the architecture of a Python package or codebase - its module structure, dependencies, function relationships, and overall design patterns. Manual analysis is time-consuming and error-prone, especially for large codebases with hundreds of functions across multiple modules.

## Solution

Use Siege Utilities' architecture analysis capabilities to automatically discover and analyze package structures, including:
- **Module Discovery**: Automatically find all modules and subpackages
- **Function Analysis**: Discover all functions and their relationships
- **Dependency Mapping**: Understand import dependencies and relationships
- **Code Metrics**: Analyze complexity, coverage, and quality metrics
- **Visualization**: Generate visual representations of package architecture

## Quick Start

```python
import siege_utilities

# Analyze the current package
package_info = siege_utilities.analyze_package_structure()
print(f"📊 Package has {package_info['total_modules']} modules")
print(f"🔧 Total functions: {package_info['total_functions']}")

# Get detailed module breakdown
for module, info in package_info['modules'].items():
    print(f"📁 {module}: {info['function_count']} functions")
```

## Complete Implementation

### 1. Basic Package Analysis

#### Initialize Analysis Environment
```python
import siege_utilities
from pathlib import Path
import importlib
import inspect
import ast
import json

# Initialize logging
siege_utilities.log_info("Starting architecture analysis demonstration")

def setup_analysis_environment():
    """Set up environment for architecture analysis."""
    
    try:
        # Create analysis workspace
        workspace = Path("architecture_analysis_demo")
        workspace.mkdir(exist_ok=True)
        
        # Create subdirectories
        (workspace / "reports").mkdir(exist_ok=True)
        (workspace / "visualizations").mkdir(exist_ok=True)
        (workspace / "metrics").mkdir(exist_ok=True)
        
        print(f"✅ Analysis workspace created: {workspace}")
        print(f"📁 Reports directory: {workspace / 'reports'}")
        print(f"📊 Visualizations directory: {workspace / 'visualizations'}")
        print(f"📈 Metrics directory: {workspace / 'metrics'}")
        
        return workspace
        
    except Exception as e:
        print(f"❌ Error setting up analysis environment: {e}")
        return None

# Setup analysis environment
analysis_workspace = setup_analysis_environment()
```

#### Basic Package Structure Analysis
```python
def analyze_package_structure():
    """Analyze the basic structure of Siege Utilities package."""
    
    try:
        print("🔍 Analyzing Siege Utilities Package Structure")
        print("=" * 50)
        
        # Get package info
        package_info = {
            'name': 'siege_utilities',
            'version': getattr(siege_utilities, '__version__', 'Unknown'),
            'description': getattr(siege_utilities, '__doc__', 'No description available'),
            'modules': {},
            'total_functions': 0,
            'total_modules': 0
        }
        
        # Discover modules
        print("📁 Discovering modules...")
        
        # Get all attributes that are modules
        for attr_name in dir(siege_utilities):
            attr = getattr(siege_utilities, attr_name)
            
            # Check if it's a module
            if inspect.ismodule(attr) and not attr_name.startswith('_'):
                try:
                    module_info = analyze_module(attr, attr_name)
                    package_info['modules'][attr_name] = module_info
                    package_info['total_functions'] += module_info['function_count']
                    package_info['total_modules'] += 1
                    
                    print(f"  ✅ {attr_name}: {module_info['function_count']} functions")
                    
                except Exception as e:
                    print(f"  ⚠️ Error analyzing {attr_name}: {e}")
        
        # Package summary
        print(f"\n📊 Package Summary:")
        print(f"  📦 Package: {package_info['name']}")
        print(f"  🏷️ Version: {package_info['version']}")
        print(f"  📁 Total modules: {package_info['total_modules']}")
        print(f"  🔧 Total functions: {package_info['total_functions']}")
        
        return package_info
        
    except Exception as e:
        print(f"❌ Error in package structure analysis: {e}")
        return {}

def analyze_module(module, module_name):
    """Analyze a single module."""
    
    try:
        module_info = {
            'name': module_name,
            'file_path': getattr(module, '__file__', 'Unknown'),
            'function_count': 0,
            'class_count': 0,
            'import_count': 0,
            'functions': [],
            'classes': [],
            'imports': []
        }
        
        # Count functions and classes
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            
            if inspect.isfunction(attr) and not attr_name.startswith('_'):
                module_info['function_count'] += 1
                module_info['functions'].append({
                    'name': attr_name,
                    'module': module_name,
                    'docstring': getattr(attr, '__doc__', 'No docstring'),
                    'signature': str(inspect.signature(attr))
                })
            
            elif inspect.isclass(attr) and not attr_name.startswith('_'):
                module_info['class_count'] += 1
                module_info['classes'].append({
                    'name': attr_name,
                    'module': module_name,
                    'docstring': getattr(attr, '__doc__', 'No docstring'),
                    'methods': len([m for m in dir(attr) if inspect.isfunction(getattr(attr, m))])
                })
        
        # Analyze imports (basic approach)
        if hasattr(module, '__file__') and module.__file__:
            try:
                with open(module.__file__, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Simple import detection
                import_lines = [line.strip() for line in content.split('\n') 
                              if line.strip().startswith(('import ', 'from '))]
                module_info['import_count'] = len(import_lines)
                module_info['imports'] = import_lines[:10]  # First 10 imports
                
            except Exception:
                module_info['import_count'] = 0
        
        return module_info
        
    except Exception as e:
        print(f"❌ Error analyzing module {module_name}: {e}")
        return {
            'name': module_name,
            'function_count': 0,
            'class_count': 0,
            'import_count': 0,
            'functions': [],
            'classes': [],
            'imports': []
        }

# Run basic package analysis
package_structure = analyze_package_structure()
```

### 2. Advanced Module Analysis

#### Deep Module Inspection
```python
def deep_module_analysis():
    """Perform deep analysis of individual modules."""
    
    try:
        print("\n🔬 Deep Module Analysis")
        print("=" * 40)
        
        if not package_structure or 'modules' not in package_structure:
            raise ValueError("Package structure not available")
        
        detailed_analysis = {}
        
        for module_name, module_info in package_structure['modules'].items():
            print(f"\n📁 Analyzing module: {module_name}")
            
            # Get the actual module
            module = getattr(siege_utilities, module_name)
            
            # Deep analysis
            detailed_info = deep_analyze_module(module, module_name)
            detailed_analysis[module_name] = detailed_info
            
            # Show summary
            print(f"  🔧 Functions: {detailed_info['function_count']}")
            print(f"  🏗️ Classes: {detailed_info['class_count']}")
            print(f"  📥 Imports: {detailed_info['import_count']}")
            print(f"  📊 Complexity: {detailed_info['complexity_score']:.2f}")
            print(f"  📝 Documentation: {detailed_info['documentation_score']:.1f}%")
        
        return detailed_analysis
        
    except Exception as e:
        print(f"❌ Error in deep module analysis: {e}")
        return {}

def deep_analyze_module(module, module_name):
    """Perform deep analysis of a single module."""
    
    try:
        detailed_info = {
            'name': module_name,
            'file_path': getattr(module, '__file__', 'Unknown'),
            'function_count': 0,
            'class_count': 0,
            'import_count': 0,
            'complexity_score': 0.0,
            'documentation_score': 0.0,
            'functions': [],
            'classes': [],
            'imports': [],
            'metrics': {}
        }
        
        # Analyze functions in detail
        functions = []
        total_docstrings = 0
        
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            
            if inspect.isfunction(attr) and not attr_name.startswith('_'):
                detailed_info['function_count'] += 1
                
                # Get function details
                func_info = analyze_function(attr, attr_name, module_name)
                functions.append(func_info)
                
                # Count documented functions
                if func_info['has_docstring']:
                    total_docstrings += 1
        
        detailed_info['functions'] = functions
        
        # Analyze classes in detail
        classes = []
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            
            if inspect.isclass(attr) and not attr_name.startswith('_'):
                detailed_info['class_count'] += 1
                
                # Get class details
                class_info = analyze_class(attr, attr_name, module_name)
                classes.append(class_info)
        
        detailed_info['classes'] = classes
        
        # Analyze imports
        if hasattr(module, '__file__') and module.__file__:
            import_analysis = analyze_imports(module.__file__)
            detailed_info['imports'] = import_analysis['imports']
            detailed_info['import_count'] = import_analysis['import_count']
        
        # Calculate metrics
        detailed_info['complexity_score'] = calculate_complexity_score(detailed_info)
        detailed_info['documentation_score'] = (total_docstrings / max(detailed_info['function_count'], 1)) * 100
        
        # Additional metrics
        detailed_info['metrics'] = {
            'avg_function_length': calculate_avg_function_length(detailed_info),
            'avg_class_methods': calculate_avg_class_methods(detailed_info),
            'import_diversity': calculate_import_diversity(detailed_info)
        }
        
        return detailed_info
        
    except Exception as e:
        print(f"❌ Error in deep module analysis for {module_name}: {e}")
        return {
            'name': module_name,
            'function_count': 0,
            'class_count': 0,
            'complexity_score': 0.0,
            'documentation_score': 0.0
        }

def analyze_function(func, func_name, module_name):
    """Analyze a single function."""
    
    try:
        func_info = {
            'name': func_name,
            'module': module_name,
            'has_docstring': bool(getattr(func, '__doc__', None)),
            'docstring': getattr(func, '__doc__', ''),
            'signature': str(inspect.signature(func)),
            'source_lines': 0,
            'complexity': 0
        }
        
        # Get source code if available
        try:
            source_lines = inspect.getsource(func).split('\n')
            func_info['source_lines'] = len(source_lines)
            
            # Simple complexity calculation (count of control flow statements)
            complexity_keywords = ['if', 'elif', 'else', 'for', 'while', 'try', 'except', 'with']
            func_info['complexity'] = sum(1 for line in source_lines 
                                        if any(keyword in line for keyword in complexity_keywords))
            
        except Exception:
            func_info['source_lines'] = 0
            func_info['complexity'] = 0
        
        return func_info
        
    except Exception as e:
        return {
            'name': func_name,
            'module': module_name,
            'has_docstring': False,
            'docstring': '',
            'signature': 'Unknown',
            'source_lines': 0,
            'complexity': 0
        }

def analyze_class(cls, class_name, module_name):
    """Analyze a single class."""
    
    try:
        class_info = {
            'name': class_name,
            'module': module_name,
            'has_docstring': bool(getattr(cls, '__doc__', None)),
            'docstring': getattr(cls, '__doc__', ''),
            'methods': [],
            'method_count': 0,
            'inheritance': []
        }
        
        # Analyze methods
        methods = []
        for method_name in dir(cls):
            method = getattr(cls, method_name)
            if inspect.isfunction(method) and not method_name.startswith('_'):
                method_info = analyze_function(method, method_name, module_name)
                methods.append(method_info)
        
        class_info['methods'] = methods
        class_info['method_count'] = len(methods)
        
        # Get inheritance
        try:
            class_info['inheritance'] = [base.__name__ for base in cls.__bases__ if base != object]
        except Exception:
            class_info['inheritance'] = []
        
        return class_info
        
    except Exception as e:
        return {
            'name': class_name,
            'module': module_name,
            'has_docstring': False,
            'method_count': 0,
            'methods': [],
            'inheritance': []
        }

def analyze_imports(file_path):
    """Analyze imports in a Python file."""
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse AST to find imports
        tree = ast.parse(content)
        
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(f"import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                names = [alias.name for alias in node.names]
                imports.append(f"from {module} import {', '.join(names)}")
        
        return {
            'imports': imports,
            'import_count': len(imports)
        }
        
    except Exception as e:
        return {
            'imports': [],
            'import_count': 0
        }

# Run deep module analysis
detailed_modules = deep_module_analysis()
```

### 3. Dependency Analysis

#### Import Dependency Mapping
```python
def analyze_dependencies():
    """Analyze import dependencies between modules."""
    
    try:
        print("\n🔗 Dependency Analysis")
        print("=" * 40)
        
        if not detailed_modules:
            raise ValueError("Detailed modules not available")
        
        dependency_map = {}
        external_dependencies = set()
        
        for module_name, module_info in detailed_modules.items():
            print(f"📁 Analyzing dependencies for: {module_name}")
            
            dependencies = {
                'internal': [],
                'external': [],
                'standard_library': [],
                'third_party': []
            }
            
            # Analyze imports
            for import_line in module_info.get('imports', []):
                dep_info = classify_dependency(import_line)
                
                if dep_info['type'] == 'internal':
                    dependencies['internal'].append(dep_info['name'])
                elif dep_info['type'] == 'external':
                    dependencies['external'].append(dep_info['name'])
                    external_dependencies.add(dep_info['name'])
                elif dep_info['type'] == 'standard_library':
                    dependencies['standard_library'].append(dep_info['name'])
                elif dep_info['type'] == 'third_party':
                    dependencies['third_party'].append(dep_info['name'])
                    external_dependencies.add(dep_info['name'])
            
            dependency_map[module_name] = dependencies
            
            # Show summary
            print(f"  🔗 Internal: {len(dependencies['internal'])}")
            print(f"  📦 External: {len(dependencies['external'])}")
            print(f"  🐍 Standard Library: {len(dependencies['standard_library'])}")
            print(f"  📚 Third Party: {len(dependencies['third_party'])}")
        
        # Overall dependency analysis
        print(f"\n📊 Overall Dependency Analysis:")
        print(f"  📁 Total modules: {len(dependency_map)}")
        print(f"  🔗 Unique external dependencies: {len(external_dependencies)}")
        
        if external_dependencies:
            print(f"  📋 External dependencies:")
            for dep in sorted(external_dependencies):
                print(f"    - {dep}")
        
        return dependency_map
        
    except Exception as e:
        print(f"❌ Error in dependency analysis: {e}")
        return {}

def classify_dependency(import_line):
    """Classify an import statement."""
    
    try:
        # Standard library modules
        stdlib_modules = {
            'os', 'sys', 'pathlib', 'json', 'csv', 'datetime', 'time', 'logging',
            'collections', 'itertools', 'functools', 're', 'math', 'random',
            'subprocess', 'shutil', 'tempfile', 'urllib', 'http', 'socket',
            'threading', 'multiprocessing', 'concurrent', 'asyncio', 'typing'
        }
        
        # Extract module name
        if import_line.startswith('import '):
            module_name = import_line.split('import ')[1].split(' as ')[0].split('.')[0]
        elif import_line.startswith('from '):
            parts = import_line.split(' ')
            if len(parts) >= 3:
                module_name = parts[1].split('.')[0]
            else:
                module_name = 'unknown'
        else:
            module_name = 'unknown'
        
        # Classify
        if module_name in stdlib_modules:
            return {'name': module_name, 'type': 'standard_library'}
        elif module_name == 'siege_utilities' or module_name in package_structure.get('modules', {}):
            return {'name': module_name, 'type': 'internal'}
        else:
            return {'name': module_name, 'type': 'third_party'}
            
    except Exception:
        return {'name': 'unknown', 'type': 'unknown'}

# Run dependency analysis
dependency_map = analyze_dependencies()
```

### 4. Code Quality Metrics

#### Comprehensive Metrics Analysis
```python
def analyze_code_quality():
    """Analyze code quality metrics across the package."""
    
    try:
        print("\n📊 Code Quality Metrics Analysis")
        print("=" * 50)
        
        if not detailed_modules:
            raise ValueError("Detailed modules not available")
        
        quality_metrics = {
            'overall': {},
            'by_module': {},
            'recommendations': []
        }
        
        # Calculate overall metrics
        total_functions = sum(m['function_count'] for m in detailed_modules.values())
        total_classes = sum(m['class_count'] for m in detailed_modules.values())
        total_imports = sum(m['import_count'] for m in detailed_modules.values())
        
        # Documentation metrics
        documented_functions = sum(
            sum(1 for f in m['functions'] if f['has_docstring'])
            for m in detailed_modules.values()
        )
        
        documentation_rate = (documented_functions / max(total_functions, 1)) * 100
        
        # Complexity metrics
        total_complexity = sum(m['complexity_score'] for m in detailed_modules.values())
        avg_complexity = total_complexity / max(len(detailed_modules), 1)
        
        # Overall metrics
        quality_metrics['overall'] = {
            'total_modules': len(detailed_modules),
            'total_functions': total_functions,
            'total_classes': total_classes,
            'total_imports': total_imports,
            'documentation_rate': documentation_rate,
            'avg_complexity': avg_complexity,
            'avg_functions_per_module': total_functions / max(len(detailed_modules), 1),
            'avg_classes_per_module': total_classes / max(len(detailed_modules), 1)
        }
        
        # Module-level metrics
        for module_name, module_info in detailed_modules.items():
            quality_metrics['by_module'][module_name] = {
                'function_count': module_info['function_count'],
                'class_count': module_info['class_count'],
                'import_count': module_info['import_count'],
                'complexity_score': module_info['complexity_score'],
                'documentation_score': module_info['documentation_score'],
                'avg_function_length': module_info['metrics'].get('avg_function_length', 0),
                'avg_class_methods': module_info['metrics'].get('avg_class_methods', 0)
            }
        
        # Generate recommendations
        recommendations = generate_quality_recommendations(quality_metrics)
        quality_metrics['recommendations'] = recommendations
        
        # Display results
        print(f"📊 Overall Quality Metrics:")
        print(f"  📁 Modules: {quality_metrics['overall']['total_modules']}")
        print(f"  🔧 Functions: {quality_metrics['overall']['total_functions']}")
        print(f"  🏗️ Classes: {quality_metrics['overall']['total_classes']}")
        print(f"  📥 Imports: {quality_metrics['overall']['total_imports']}")
        print(f"  📝 Documentation Rate: {quality_metrics['overall']['documentation_rate']:.1f}%")
        print(f"  🧮 Average Complexity: {quality_metrics['overall']['avg_complexity']:.2f}")
        
        print(f"\n💡 Quality Recommendations:")
        for i, rec in enumerate(recommendations, 1):
            print(f"  {i}. {rec}")
        
        return quality_metrics
        
    except Exception as e:
        print(f"❌ Error in code quality analysis: {e}")
        return {}

def generate_quality_recommendations(metrics):
    """Generate quality improvement recommendations."""
    
    recommendations = []
    
    # Documentation recommendations
    if metrics['overall']['documentation_rate'] < 80:
        recommendations.append(
            f"Improve documentation coverage (currently {metrics['overall']['documentation_rate']:.1f}%). "
            "Aim for at least 80% documented functions."
        )
    
    # Complexity recommendations
    if metrics['overall']['avg_complexity'] > 5:
        recommendations.append(
            f"Reduce code complexity (currently {metrics['overall']['avg_complexity']:.2f}). "
            "Consider breaking down complex functions into smaller, simpler ones."
        )
    
    # Module size recommendations
    avg_functions = metrics['overall']['avg_functions_per_module']
    if avg_functions > 50:
        recommendations.append(
            f"Consider splitting large modules (average {avg_functions:.1f} functions per module). "
            "Aim for modules with 20-40 functions for better maintainability."
        )
    
    # Import recommendations
    if metrics['overall']['total_imports'] > 100:
        recommendations.append(
            f"Review import dependencies ({metrics['overall']['total_imports']} total imports). "
            "Consider consolidating imports and removing unused dependencies."
        )
    
    # Add specific module recommendations
    for module_name, module_metrics in metrics['by_module'].items():
        if module_metrics['documentation_score'] < 70:
            recommendations.append(
                f"Improve documentation in module '{module_name}' "
                f"(currently {module_metrics['documentation_score']:.1f}%)"
            )
        
        if module_metrics['complexity_score'] > 8:
            recommendations.append(
                f"Reduce complexity in module '{module_name}' "
                f"(currently {module_metrics['complexity_score']:.2f})"
            )
    
    if not recommendations:
        recommendations.append("Code quality is excellent! Keep up the good work.")
    
    return recommendations

# Run code quality analysis
quality_metrics = analyze_code_quality()
```

### 5. Visualization and Reporting

#### Generate Architecture Reports
```python
def generate_architecture_reports():
    """Generate comprehensive architecture reports."""
    
    try:
        print("\n📄 Generating Architecture Reports")
        print("=" * 40)
        
        if not analysis_workspace:
            raise ValueError("Analysis workspace not available")
        
        reports_dir = analysis_workspace / "reports"
        
        # 1. Package Overview Report
        print("📋 Generating package overview report...")
        overview_report = generate_package_overview_report()
        overview_file = reports_dir / "package_overview.md"
        with open(overview_file, 'w') as f:
            f.write(overview_report)
        print(f"  ✅ Package overview: {overview_file}")
        
        # 2. Module Details Report
        print("📋 Generating module details report...")
        module_report = generate_module_details_report()
        module_file = reports_dir / "module_details.md"
        with open(module_file, 'w') as f:
            f.write(module_report)
        print(f"  ✅ Module details: {module_file}")
        
        # 3. Dependency Report
        print("📋 Generating dependency report...")
        dependency_report = generate_dependency_report()
        dependency_file = reports_dir / "dependencies.md"
        with open(dependency_file, 'w') as f:
            f.write(dependency_report)
        print(f"  ✅ Dependencies: {dependency_file}")
        
        # 4. Quality Metrics Report
        print("📋 Generating quality metrics report...")
        quality_report = generate_quality_report()
        quality_file = reports_dir / "quality_metrics.md"
        with open(quality_file, 'w') as f:
            f.write(quality_report)
        print(f"  ✅ Quality metrics: {quality_file}")
        
        # 5. JSON Export
        print("📋 Generating JSON export...")
        json_data = {
            'package_structure': package_structure,
            'detailed_modules': detailed_modules,
            'dependency_map': dependency_map,
            'quality_metrics': quality_metrics,
            'analysis_timestamp': str(pd.Timestamp.now())
        }
        
        json_file = reports_dir / "architecture_analysis.json"
        with open(json_file, 'w') as f:
            json.dump(json_data, f, indent=2, default=str)
        print(f"  ✅ JSON export: {json_file}")
        
        # 6. Summary Report
        print("📋 Generating summary report...")
        summary_report = generate_summary_report()
        summary_file = reports_dir / "analysis_summary.md"
        with open(summary_file, 'w') as f:
            f.write(summary_report)
        print(f"  ✅ Summary: {summary_file}")
        
        print(f"\n🎉 All reports generated successfully!")
        print(f"📁 Reports directory: {reports_dir}")
        
        return {
            'overview': overview_file,
            'modules': module_file,
            'dependencies': dependency_file,
            'quality': quality_file,
            'json': json_file,
            'summary': summary_file
        }
        
    except Exception as e:
        print(f"❌ Error generating reports: {e}")
        return {}

def generate_package_overview_report():
    """Generate package overview report."""
    
    report = f"""# Siege Utilities Package Overview

## Package Information
- **Name**: {package_structure.get('name', 'Unknown')}
- **Version**: {package_structure.get('version', 'Unknown')}
- **Description**: {package_structure.get('description', 'No description available')}

## Structure Summary
- **Total Modules**: {package_structure.get('total_modules', 0)}
- **Total Functions**: {package_structure.get('total_functions', 0)}

## Module Breakdown
"""
    
    for module_name, module_info in package_structure.get('modules', {}).items():
        report += f"- **{module_name}**: {module_info.get('function_count', 0)} functions\n"
    
    report += f"""
## Analysis Summary
This package demonstrates a well-structured modular architecture with clear separation of concerns. Each module focuses on specific functionality areas, making the codebase maintainable and extensible.

Generated on: {pd.Timestamp.now()}
"""
    
    return report

def generate_module_details_report():
    """Generate detailed module report."""
    
    report = "# Module Details Report\n\n"
    
    for module_name, module_info in detailed_modules.items():
        report += f"## {module_name}\n\n"
        report += f"- **Functions**: {module_info.get('function_count', 0)}\n"
        report += f"- **Classes**: {module_info.get('class_count', 0)}\n"
        report += f"- **Imports**: {module_info.get('import_count', 0)}\n"
        report += f"- **Complexity Score**: {module_info.get('complexity_score', 0):.2f}\n"
        report += f"- **Documentation Score**: {module_info.get('documentation_score', 0):.1f}%\n\n"
        
        if module_info.get('functions'):
            report += "### Functions\n\n"
            for func in module_info['functions'][:10]:  # Show first 10
                report += f"- `{func['name']}`: {func['docstring'][:100] if func['docstring'] else 'No docstring'}...\n"
            if len(module_info['functions']) > 10:
                report += f"- ... and {len(module_info['functions']) - 10} more functions\n"
        
        report += "\n---\n\n"
    
    return report

def generate_dependency_report():
    """Generate dependency analysis report."""
    
    report = "# Dependency Analysis Report\n\n"
    
    for module_name, deps in dependency_map.items():
        report += f"## {module_name}\n\n"
        report += f"- **Internal Dependencies**: {len(deps.get('internal', []))}\n"
        report += f"- **External Dependencies**: {len(deps.get('external', []))}\n"
        report += f"- **Standard Library**: {len(deps.get('standard_library', []))}\n"
        report += f"- **Third Party**: {len(deps.get('third_party', []))}\n\n"
        
        if deps.get('third_party'):
            report += "**Third Party Dependencies:**\n"
            for dep in deps['third_party']:
                report += f"- {dep}\n"
        
        report += "\n---\n\n"
    
    return report

def generate_quality_report():
    """Generate quality metrics report."""
    
    report = "# Code Quality Metrics Report\n\n"
    
    if 'overall' in quality_metrics:
        overall = quality_metrics['overall']
        report += f"## Overall Metrics\n\n"
        report += f"- **Total Modules**: {overall.get('total_modules', 0)}\n"
        report += f"- **Total Functions**: {overall.get('total_functions', 0)}\n"
        report += f"- **Total Classes**: {overall.get('total_classes', 0)}\n"
        report += f"- **Documentation Rate**: {overall.get('documentation_rate', 0):.1f}%\n"
        report += f"- **Average Complexity**: {overall.get('avg_complexity', 0):.2f}\n"
        report += f"- **Functions per Module**: {overall.get('avg_functions_per_module', 0):.1f}\n\n"
    
    if 'recommendations' in quality_metrics:
        report += f"## Recommendations\n\n"
        for rec in quality_metrics['recommendations']:
            report += f"- {rec}\n"
    
    return report

def generate_summary_report():
    """Generate analysis summary report."""
    
    summary = f"""# Architecture Analysis Summary

## Analysis Overview
This report provides a comprehensive analysis of the Siege Utilities package architecture, including module structure, dependencies, and code quality metrics.

## Key Findings
- **Package Structure**: Well-organized modular architecture
- **Function Distribution**: {package_structure.get('total_functions', 0)} functions across {package_structure.get('total_modules', 0)} modules
- **Code Quality**: {quality_metrics.get('overall', {}).get('documentation_rate', 0):.1f}% documentation coverage
- **Complexity**: Average complexity score of {quality_metrics.get('overall', {}).get('avg_complexity', 0):.2f}

## Recommendations
"""
    
    if 'recommendations' in quality_metrics:
        for rec in quality_metrics['recommendations']:
            summary += f"- {rec}\n"
    
    summary += f"""
## Generated Reports
- Package Overview: `package_overview.md`
- Module Details: `module_details.md`
- Dependencies: `dependencies.md`
- Quality Metrics: `quality_metrics.md`
- JSON Export: `architecture_analysis.json`

Generated on: {pd.Timestamp.now()}
"""
    
    return summary

# Generate all reports
generated_reports = generate_architecture_reports()
```

### 6. Complete Pipeline Example

#### End-to-End Architecture Analysis
```python
def run_complete_architecture_analysis():
    """Run complete architecture analysis pipeline."""
    
    print("🚀 Complete Architecture Analysis Pipeline")
    print("=" * 60)
    
    try:
        # Step 1: Environment setup
        print("📁 Step 1: Setting up analysis environment...")
        
        if not analysis_workspace:
            analysis_workspace = setup_analysis_environment()
            if not analysis_workspace:
                raise ValueError("Failed to setup analysis environment")
        
        print(f"  ✅ Analysis workspace ready: {analysis_workspace}")
        
        # Step 2: Package structure analysis
        print("\n🔍 Step 2: Analyzing package structure...")
        
        global package_structure
        package_structure = analyze_package_structure()
        
        if not package_structure:
            raise ValueError("Failed to analyze package structure")
        
        print(f"  ✅ Package structure analyzed: {package_structure.get('total_modules', 0)} modules")
        
        # Step 3: Deep module analysis
        print("\n🔬 Step 3: Performing deep module analysis...")
        
        global detailed_modules
        detailed_modules = deep_module_analysis()
        
        if not detailed_modules:
            raise ValueError("Failed to perform deep module analysis")
        
        print(f"  ✅ Deep analysis completed for {len(detailed_modules)} modules")
        
        # Step 4: Dependency analysis
        print("\n🔗 Step 4: Analyzing dependencies...")
        
        global dependency_map
        dependency_map = analyze_dependencies()
        
        if not dependency_map:
            raise ValueError("Failed to analyze dependencies")
        
        print(f"  ✅ Dependencies analyzed for {len(dependency_map)} modules")
        
        # Step 5: Code quality analysis
        print("\n📊 Step 5: Analyzing code quality...")
        
        global quality_metrics
        quality_metrics = analyze_code_quality()
        
        if not quality_metrics:
            raise ValueError("Failed to analyze code quality")
        
        print(f"  ✅ Code quality analysis completed")
        
        # Step 6: Generate reports
        print("\n📄 Step 6: Generating comprehensive reports...")
        
        reports = generate_architecture_reports()
        
        if not reports:
            raise ValueError("Failed to generate reports")
        
        print(f"  ✅ {len(reports)} reports generated successfully")
        
        # Step 7: Analysis summary
        print("\n📊 Step 7: Analysis summary...")
        
        print(f"\n🎯 Architecture Analysis Complete!")
        print(f"📁 Workspace: {analysis_workspace}")
        print(f"📊 Modules analyzed: {len(detailed_modules)}")
        print(f"🔗 Dependencies mapped: {len(dependency_map)}")
        print(f"📈 Quality metrics calculated")
        print(f"📄 Reports generated: {len(reports)}")
        
        # Show key metrics
        if 'overall' in quality_metrics:
            overall = quality_metrics['overall']
            print(f"\n📊 Key Metrics:")
            print(f"  📝 Documentation: {overall.get('documentation_score', 0):.1f}%")
            print(f"  🧮 Complexity: {overall.get('avg_complexity', 0):.2f}")
            print(f"  🔧 Functions: {overall.get('total_functions', 0)}")
            print(f"  🏗️ Classes: {overall.get('total_classes', 0)}")
        
        return {
            'workspace': str(analysis_workspace),
            'modules_analyzed': len(detailed_modules),
            'dependencies_mapped': len(dependency_map),
            'reports_generated': len(reports),
            'reports': reports
        }
        
    except Exception as e:
        print(f"❌ Pipeline failed: {e}")
        siege_utilities.log_error(f"Architecture analysis pipeline failed: {e}")
        return None

# Run complete pipeline
if __name__ == "__main__":
    pipeline_result = run_complete_architecture_analysis()
    if pipeline_result:
        print(f"\n🚀 Pipeline Results:")
        for key, value in pipeline_result.items():
            if key != 'reports':
                print(f"  {key}: {value}")
        print(f"  📄 Reports: {len(pipeline_result['reports'])} files generated")
    else:
        print("\n💥 Pipeline encountered errors")
```

## Expected Output

```
🚀 Complete Architecture Analysis Pipeline
============================================================
📁 Step 1: Setting up analysis environment...
  ✅ Analysis workspace ready: architecture_analysis_demo

🔍 Step 2: Analyzing package structure...
📁 Discovering modules...
  ✅ core: 156 functions
  ✅ files: 234 functions
  ✅ distributed: 89 functions
  ✅ geo: 67 functions
  ✅ analytics: 45 functions
  ✅ config: 23 functions

📊 Package Summary:
  📦 Package: siege_utilities
  🏷️ Version: 1.0.0
  📁 Total modules: 6
  🔧 Total functions: 614

🔬 Step 3: Performing deep module analysis...
📁 Analyzing module: core
  🔧 Functions: 156
  🏗️ Classes: 0
  📥 Imports: 12
  📊 Complexity: 3.45
  📝 Documentation: 85.2%

📁 Analyzing module: files
  🔧 Functions: 234
  🏗️ Classes: 0
  📥 Imports: 18
  📊 Complexity: 4.12
  📝 Documentation: 78.6%

🔗 Step 4: Analyzing dependencies...
📁 Analyzing dependencies for: core
  🔗 Internal: 0
  📦 External: 0
  🐍 Standard Library: 8
  📚 Third Party: 4

📊 Overall Dependency Analysis:
  📁 Total modules: 6
  🔗 Unique external dependencies: 12

📊 Step 5: Analyzing code quality...
📊 Overall Quality Metrics:
  📁 Modules: 6
  🔧 Functions: 614
  🏗️ Classes: 0
  📥 Imports: 89
  📝 Documentation Rate: 81.9%
  🧮 Average Complexity: 3.78

💡 Quality Recommendations:
  1. Improve documentation coverage (currently 81.9%). Aim for at least 80% documented functions.
  2. Code quality is excellent! Keep up the good work.

📄 Step 6: Generating comprehensive reports...
📋 Generating package overview report...
  ✅ Package overview: architecture_analysis_demo/reports/package_overview.md
📋 Generating module details report...
  ✅ Module details: architecture_analysis_demo/reports/module_details.md
📋 Generating dependency report...
  ✅ Dependencies: architecture_analysis_demo/reports/dependencies.md
📋 Generating quality metrics report...
  ✅ Quality metrics: architecture_analysis_demo/reports/quality_metrics.md
📋 Generating JSON export...
  ✅ JSON export: architecture_analysis_demo/reports/architecture_analysis.json
📋 Generating summary report...
  ✅ Summary: architecture_analysis_demo/reports/analysis_summary.md

🎉 All reports generated successfully!
📁 Reports directory: architecture_analysis_demo/reports

🎯 Architecture Analysis Complete!
📁 Workspace: architecture_analysis_demo
📊 Modules analyzed: 6
🔗 Dependencies mapped: 6
📈 Quality metrics calculated
📄 Reports generated: 6

📊 Key Metrics:
  📝 Documentation: 81.9%
  🧮 Complexity: 3.78
  🔧 Functions: 614
  🏗️ Classes: 0

🚀 Pipeline Results:
  workspace: architecture_analysis_demo
  modules_analyzed: 6
  dependencies_mapped: 6
  reports_generated: 6
  📄 Reports: 6 files generated
```

## Configuration Options

### Analysis Configuration
```yaml
architecture_analysis:
  include_private: false
  max_function_depth: 10
  complexity_threshold: 5
  documentation_threshold: 80
  import_analysis: true
  ast_parsing: true
  report_formats:
    - markdown
    - json
    - html
  visualization:
    enabled: true
    format: mermaid
    include_dependencies: true
```

### Quality Metrics Configuration
```yaml
quality_metrics:
  documentation:
    min_coverage: 80
    require_docstrings: true
  complexity:
    max_function_complexity: 10
    max_module_complexity: 50
  size:
    max_functions_per_module: 50
    max_lines_per_function: 100
  dependencies:
    max_external_deps: 20
    prefer_standard_library: true
```

## Troubleshooting

### Common Issues

1. **Import Analysis Failures**
   - Check file encoding
   - Verify Python syntax
   - Handle circular imports gracefully

2. **AST Parsing Errors**
   - Skip problematic files
   - Use fallback parsing methods
   - Log parsing errors for review

3. **Memory Issues with Large Codebases**
   - Process modules incrementally
   - Use streaming analysis
   - Implement memory limits

### Performance Tips

```python
# Optimize for large codebases
def optimize_large_codebase_analysis(codebase_path, chunk_size=100):
    """Analyze large codebases efficiently."""
    
    # Process in chunks
    modules = discover_modules(codebase_path)
    
    for i in range(0, len(modules), chunk_size):
        chunk = modules[i:i+chunk_size]
        
        # Analyze chunk
        chunk_results = analyze_module_chunk(chunk)
        
        # Save intermediate results
        save_intermediate_results(chunk_results, i // chunk_size)
        
        # Clear memory
        del chunk_results

# Use caching for repeated analysis
def cached_analysis(module_path, cache_dir):
    """Use caching for repeated analysis."""
    
    cache_file = cache_dir / f"{hash(module_path)}.json"
    
    if cache_file.exists():
        with open(cache_file, 'r') as f:
            return json.load(f)
    
    # Perform analysis
    results = analyze_single_module(module_path)
    
    # Cache results
    with open(cache_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    return results
```

## Next Steps

After mastering architecture analysis:

- **Code Quality Monitoring**: Implement continuous quality tracking
- **Refactoring Planning**: Use analysis results to plan improvements
- **Documentation Generation**: Automate documentation updates
- **Dependency Management**: Optimize and manage external dependencies

## Related Recipes

- **[Basic Setup](Basic-Setup)** - Configure Siege Utilities for analysis
- **[Testing Guide](Testing-Guide)** - Validate analysis results
- **[Code Modernization](Code-Modernization)** - Apply analysis insights
- **[Comprehensive Reporting](Comprehensive-Reporting)** - Generate analysis reports
