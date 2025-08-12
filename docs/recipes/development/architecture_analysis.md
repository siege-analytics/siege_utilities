# Architecture Analysis and Diagram Generation

## Problem
You need to understand the structure of the Siege Utilities package, analyze its components, and generate visual representations of the architecture for documentation or development purposes.

## Solution
Use the built-in architecture analysis tools to dynamically generate package structure diagrams and analyze the codebase structure.

## Code Example

### 1. Basic Architecture Analysis
```python
import siege_utilities

# Analyze the package structure
structure = siege_utilities.analyze_package_structure()

print(f"Package: {structure['package_name']}")
print(f"Total Functions: {structure['total_functions']}")
print(f"Total Classes: {structure['total_classes']}")
print(f"Modules: {structure['module_count']}")
```

### 2. Generate Text Architecture Diagram
```python
# Generate a text-based architecture diagram
text_diagram = siege_utilities.generate_architecture_diagram(
    output_format="text",
    include_details=True
)

print(text_diagram)
```

### 3. Generate Markdown Architecture Diagram
```python
# Generate a markdown diagram for documentation
markdown_diagram = siege_utilities.generate_architecture_diagram(
    output_format="markdown",
    include_details=True
)

# Save to file
with open("architecture_diagram.md", "w") as f:
    f.write(markdown_diagram)
```

### 4. Generate RST Architecture Diagram
```python
# Generate reStructuredText for Sphinx documentation
rst_diagram = siege_utilities.generate_architecture_diagram(
    output_format="rst",
    include_details=True
)

# Save to file
with open("architecture_diagram.rst", "w") as f:
    f.write(rst_diagram)
```

### 5. Generate JSON Output for Analysis
```python
# Generate JSON output for programmatic analysis
json_output = siege_utilities.generate_architecture_diagram(
    output_format="json",
    include_details=False  # Exclude detailed info for cleaner JSON
)

# Parse and analyze the JSON
import json
data = json.loads(json_output)

# Find the largest module
largest_module = max(data['modules'].items(), 
                    key=lambda x: x[1]['function_count'])
print(f"Largest module: {largest_module[0]} with {largest_module[1]['function_count']} functions")
```

### 6. Command Line Usage
```bash
# Generate text diagram
python -m siege_utilities.development.architecture

# Generate markdown diagram
python -m siege_utilities.development.architecture --format markdown

# Generate RST diagram
python -m siege_utilities.development.architecture --format rst

# Generate JSON output
python -m siege_utilities.development.architecture --format json

# Save to file
python -m siege_utilities.development.architecture --output architecture.txt

# Generate without detailed information
python -m siege_utilities.development.architecture --no-details
```

### 7. Advanced Analysis and Customization
```python
# Analyze specific modules
structure = siege_utilities.analyze_package_structure()

# Focus on specific areas
for module_name, module_info in structure['modules'].items():
    if module_info['function_count'] > 100:  # Large modules
        print(f"Large module: {module_name}")
        print(f"  Functions: {module_info['function_count']}")
        print(f"  Classes: {module_info['class_count']}")
        
        # Show some function examples
        if module_info.get('functions'):
            print("  Sample functions:")
            for func_name in list(module_info['functions'].keys())[:3]:
                print(f"    - {func_name}")
        print()

# Analyze function distribution
function_counts = [
    (name, info['function_count']) 
    for name, info in structure['modules'].items()
]
function_counts.sort(key=lambda x: x[1], reverse=True)

print("Modules by function count:")
for name, count in function_counts[:5]:
    print(f"  {name}: {count} functions")
```

### 8. Integration with Documentation Workflow
```python
# Generate architecture diagram for documentation
def update_architecture_documentation():
    """Update architecture documentation with current package structure"""
    
    # Generate RST diagram
    rst_diagram = siege_utilities.generate_architecture_diagram(
        output_format="rst",
        include_details=True
    )
    
    # Save to docs directory
    docs_dir = "docs/source"
    with open(f"{docs_dir}/current_architecture.rst", "w") as f:
        f.write(rst_diagram)
    
    print("Architecture documentation updated!")

# Generate markdown for GitHub wiki
def update_wiki_architecture():
    """Update wiki with current architecture"""
    
    markdown_diagram = siege_utilities.generate_architecture_diagram(
        output_format="markdown",
        include_details=True
    )
    
    with open("wiki/architecture.md", "w") as f:
        f.write(markdown_diagram)
    
    print("Wiki architecture updated!")
```

## Expected Output

```
Package: siege_utilities
Total Functions: 1147
Total Classes: 191
Modules: 25

📦 core/
  🔧 Functions (16):
    - log_info, log_warning, log_error, log_debug, log_critical
    - init_logger, get_logger, configure_shared_logging
    - remove_wrapping_quotes_and_trim
    ... and 8 more
  🏗️  Classes (0):

📦 distributed/
  🔧 Functions (466):
    - abs, acos, acosh, add_months, aes_decrypt
    - aggregate, any_value, approx_count_distinct
    ... and 461 more
  🏗️  Classes (14):
    - Any, ArrayType, Column
    ... and 11 more

📦 files/
  🔧 Functions (22):
    - calculate_file_hash, generate_sha256_hash_for_file
    - check_if_file_exists_at_path, delete_existing_file_and_replace_it_with_an_empty_file
    ... and 18 more
  🏗️  Classes (0):
```

## Notes

- **Performance**: Analysis is performed at runtime and may take a moment for large packages
- **Memory Usage**: Detailed analysis loads all module information into memory
- **Accuracy**: Results reflect the current state of the package at runtime
- **Formats**: Supports text, markdown, RST, and JSON output formats
- **Customization**: Can include or exclude detailed function/class information
- **Integration**: Works seamlessly with documentation and wiki workflows

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure the package is properly installed and accessible
2. **Memory Issues**: Use `include_details=False` for very large packages
3. **Format Errors**: Check that the specified output format is supported
4. **File Permissions**: Ensure write permissions for output files

### Performance Tips

- Use `include_details=False` for quick overviews
- Generate JSON output for programmatic analysis
- Save results to files to avoid regenerating diagrams
- Use specific module analysis for focused insights

### Next Steps

After mastering architecture analysis:
- [Generate Documentation](../hygiene/generate_docstrings.md)
- [Create Custom Recipes](basic_setup.md)
- [Set up Automated Workflows](../system_admin/log_management.md)
- [Contribute to Package Development](../getting_started/first_steps.md)
