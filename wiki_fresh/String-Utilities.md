# String Utilities Recipe

## Overview
This recipe demonstrates how to use the string utilities in `siege_utilities` for efficient text processing, manipulation, validation, and analysis.

## Prerequisites
- Python 3.7+
- `siege_utilities` library installed
- Basic understanding of string operations and regular expressions
- Required dependencies: `regex`, `unidecode` (optional)

## Installation
```bash
pip install siege_utilities
pip install regex unidecode  # Optional but recommended
```

## Basic String Operations

### 1. String Validation and Cleaning

```python
from siege_utilities.core.string_utils import StringUtils

# Initialize string utilities
string_utils = StringUtils()

# Check if string is empty or whitespace
is_empty = string_utils.is_empty("   ")
is_whitespace = string_utils.is_whitespace("   ")
print(f"Is empty: {is_empty}")
print(f"Is whitespace: {is_whitespace}")

# Clean and normalize strings
cleaned = string_utils.clean_string("  Hello,   World!  ")
print(f"Cleaned: '{cleaned}'")

# Remove extra whitespace
normalized = string_utils.normalize_whitespace("  multiple    spaces   here  ")
print(f"Normalized: '{normalized}'")
```

### 2. String Formatting and Case Operations

```python
# Case conversions
title_case = string_utils.to_title_case("hello world")
camel_case = string_utils.to_camel_case("hello world")
snake_case = string_utils.to_snake_case("HelloWorld")
kebab_case = string_utils.to_kebab_case("Hello World")

print(f"Title case: {title_case}")
print(f"Camel case: {camel_case}")
print(f"Snake case: {snake_case}")
print(f"Kebab case: {kebab_case}")

# Format strings with placeholders
formatted = string_utils.format_string(
    "Hello {name}, you are {age} years old",
    name="Alice",
    age=30
)
print(f"Formatted: {formatted}")
```

### 3. String Searching and Matching

```python
# Check if string contains substring
contains = string_utils.contains("Hello World", "World")
starts_with = string_utils.starts_with("Hello World", "Hello")
ends_with = string_utils.ends_with("Hello World", "World")

print(f"Contains 'World': {contains}")
print(f"Starts with 'Hello': {starts_with}")
print(f"Ends with 'World': {ends_with}")

# Find substring positions
first_pos = string_utils.find_first("Hello World World", "World")
last_pos = string_utils.find_last("Hello World World", "World")
all_positions = string_utils.find_all("Hello World World", "World")

print(f"First position: {first_pos}")
print(f"Last position: {last_pos}")
print(f"All positions: {all_positions}")
```

## Advanced String Processing

### 1. Regular Expression Operations

```python
# Match patterns
email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
is_email = string_utils.matches_pattern("user@example.com", email_pattern)
print(f"Is valid email: {is_email}")

# Extract patterns
phone_pattern = r'(\d{3})-(\d{3})-(\d{4})'
phone_matches = string_utils.extract_patterns("Call 555-123-4567", phone_pattern)
print(f"Phone matches: {phone_matches}")

# Replace patterns
replaced = string_utils.replace_pattern(
    "Hello 123 World 456",
    r'\d+',
    'NUMBER'
)
print(f"Replaced: {replaced}")
```

### 2. String Transformation

```python
# Remove special characters
clean_text = string_utils.remove_special_chars("Hello@#$%^&*()World!")
print(f"Clean text: {clean_text}")

# Remove accents and diacritics
no_accents = string_utils.remove_accents("café naïve résumé")
print(f"No accents: {no_accents}")

# Convert to ASCII
ascii_text = string_utils.to_ascii("Hello 世界")
print(f"ASCII: {ascii_text}")

# Slugify for URLs
slug = string_utils.slugify("Hello World! This is a test.")
print(f"Slug: {slug}")
```

### 3. String Analysis

```python
# Count characters and words
char_count = string_utils.count_characters("Hello World")
word_count = string_utils.count_words("Hello World")
line_count = string_utils.count_lines("Line 1\nLine 2\nLine 3")

print(f"Characters: {char_count}")
print(f"Words: {word_count}")
print(f"Lines: {line_count}")

# Analyze string content
analysis = string_utils.analyze_string("Hello123World!")
print(f"Has letters: {analysis['has_letters']}")
print(f"Has digits: {analysis['has_digits']}")
print(f"Has special: {analysis['has_special']}")
print(f"Length: {analysis['length']}")
```

## Text Processing and Manipulation

### 1. Text Cleaning and Normalization

```python
# Clean HTML tags
html_text = "<p>Hello <b>World</b>!</p>"
clean_text = string_utils.remove_html_tags(html_text)
print(f"Clean text: {clean_text}")

# Normalize unicode
unicode_text = "café naïve résumé"
normalized = string_utils.normalize_unicode(unicode_text)
print(f"Normalized: {normalized}")

# Remove control characters
control_text = "Hello\x00World\x01\x02"
clean_text = string_utils.remove_control_chars(control_text)
print(f"Clean text: {clean_text}")
```

### 2. Text Parsing and Extraction

```python
# Parse CSV-like strings
csv_string = "name,age,city\nJohn,30,NYC\nJane,25,LA"
parsed = string_utils.parse_csv_string(csv_string)
print(f"Parsed CSV: {parsed}")

# Extract numbers
text_with_numbers = "The price is $123.45 and quantity is 42"
numbers = string_utils.extract_numbers(text_with_numbers)
print(f"Numbers: {numbers}")

# Extract emails
text_with_emails = "Contact us at user@example.com or support@test.org"
emails = string_utils.extract_emails(text_with_emails)
print(f"Emails: {emails}")
```

### 3. Text Generation and Templates

```python
# Generate random strings
random_string = string_utils.generate_random_string(length=10)
print(f"Random string: {random_string}")

# Generate UUID
uuid_string = string_utils.generate_uuid()
print(f"UUID: {uuid_string}")

# Fill templates
template = "Hello {name}, your order #{order_id} is ready"
filled = string_utils.fill_template(template, name="Alice", order_id="12345")
print(f"Filled template: {filled}")
```

## String Validation and Sanitization

### 1. Input Validation

```python
# Validate email format
emails = [
    "user@example.com",
    "invalid-email",
    "user@.com",
    "user@example."
]

for email in emails:
    is_valid = string_utils.is_valid_email(email)
    print(f"{email}: {is_valid}")

# Validate phone number
phone_numbers = [
    "555-123-4567",
    "555.123.4567",
    "(555) 123-4567",
    "invalid"
]

for phone in phone_numbers:
    is_valid = string_utils.is_valid_phone(phone)
    print(f"{phone}: {is_valid}")
```

### 2. Data Sanitization

```python
# Sanitize for database
db_safe = string_utils.sanitize_for_database("User's data with 'quotes'")
print(f"DB safe: {db_safe}")

# Sanitize for HTML
html_safe = string_utils.sanitize_for_html("<script>alert('xss')</script>")
print(f"HTML safe: {html_safe}")

# Sanitize for file names
file_safe = string_utils.sanitize_filename("file/with\\invalid:chars*.txt")
print(f"File safe: {file_safe}")
```

### 3. Content Filtering

```python
# Filter profanity
text_with_profanity = "This is a bad word and another bad word"
filtered = string_utils.filter_profanity(text_with_profanity)
print(f"Filtered: {filtered}")

# Filter sensitive information
text_with_sensitive = "My SSN is 123-45-6789 and CC is 1234-5678-9012-3456"
filtered = string_utils.filter_sensitive_info(text_with_sensitive)
print(f"Filtered: {filtered}")
```

## Performance Optimization

### 1. String Caching

```python
import time

# Without caching
start_time = time.time()
for i in range(1000):
    result = string_utils.clean_string("  test string  ")
end_time = time.time()
print(f"Without caching: {end_time - start_time:.4f}s")

# With caching
string_utils.enable_caching()
start_time = time.time()
for i in range(1000):
    result = string_utils.clean_string("  test string  ")
end_time = time.time()
print(f"With caching: {end_time - start_time:.4f}s")
```

### 2. Batch Processing

```python
# Process multiple strings at once
strings = [
    "  hello world  ",
    "  another string  ",
    "  third string  "
]

# Batch clean
cleaned_batch = string_utils.batch_clean(strings)
print(f"Batch cleaned: {cleaned_batch}")

# Batch transform
transformed_batch = string_utils.batch_transform(
    strings,
    'to_title_case'
)
print(f"Batch transformed: {transformed_batch}")
```

## Integration Examples

### 1. With Data Processing

```python
import pandas as pd

# Load data
df = pd.read_csv("data.csv")
print(f"Original data: {len(df)} rows")

# Clean string columns
string_columns = df.select_dtypes(include=['object']).columns

for col in string_columns:
    df[col] = df[col].apply(string_utils.clean_string)

# Remove duplicates after cleaning
df_cleaned = df.drop_duplicates()
print(f"Cleaned data: {len(df_cleaned)} rows")

# Save cleaned data
df_cleaned.to_csv("cleaned_data.csv", index=False)
```

### 2. With Web Applications

```python
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/clean-text', methods=['POST'])
def clean_text():
    data = request.get_json()
    text = data.get('text', '')
    
    if not text:
        return jsonify({'error': 'Text required'}), 400
    
    try:
        cleaned = string_utils.clean_string(text)
        normalized = string_utils.normalize_whitespace(cleaned)
        
        return jsonify({
            'success': True,
            'original': text,
            'cleaned': cleaned,
            'normalized': normalized
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True)
```

### 3. With Log Processing

```python
def process_log_file(log_file_path):
    """Process log file and extract structured information"""
    
    extracted_data = []
    
    with open(log_file_path, 'r') as f:
        for line in f:
            # Clean the log line
            cleaned_line = string_utils.clean_string(line)
            
            # Extract timestamp
            timestamp_match = string_utils.extract_patterns(
                cleaned_line,
                r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})'
            )
            
            # Extract log level
            level_match = string_utils.extract_patterns(
                cleaned_line,
                r'(INFO|WARNING|ERROR|DEBUG)'
            )
            
            # Extract message
            message_match = string_utils.extract_patterns(
                cleaned_line,
                r'\[.*?\]\s*(.+)'
            )
            
            if timestamp_match and level_match and message_match:
                extracted_data.append({
                    'timestamp': timestamp_match[0],
                    'level': level_match[0],
                    'message': message_match[0].strip()
                })
    
    return extracted_data

# Process logs
log_data = process_log_file("application.log")
print(f"Extracted {len(log_data)} log entries")
```

## Error Handling and Validation

### 1. Input Validation

```python
def validate_string_input(text, min_length=1, max_length=1000):
    """Validate string input with length constraints"""
    
    if not isinstance(text, str):
        raise ValueError("Input must be a string")
    
    if string_utils.is_empty(text):
        raise ValueError("Input cannot be empty")
    
    if len(text) < min_length:
        raise ValueError(f"Input too short (minimum {min_length} characters)")
    
    if len(text) > max_length:
        raise ValueError(f"Input too long (maximum {max_length} characters)")
    
    return True

# Use validation
try:
    validate_string_input("Hello World", min_length=5, max_length=50)
    print("Input validation passed")
except ValueError as e:
    print(f"Validation error: {e}")
```

### 2. Safe String Operations

```python
def safe_string_operation(operation_func, text, *args, **kwargs):
    """Safely execute string operations with error handling"""
    
    try:
        # Validate input
        if not isinstance(text, str):
            raise ValueError("Input must be a string")
        
        # Execute operation
        result = operation_func(text, *args, **kwargs)
        
        # Validate output
        if result is None:
            raise ValueError("Operation returned None")
        
        return result
        
    except Exception as e:
        print(f"String operation failed: {e}")
        return text  # Return original text as fallback

# Use safe operations
cleaned = safe_string_operation(
    string_utils.clean_string,
    "  Hello World  "
)
print(f"Safe cleaned: '{cleaned}'")
```

## Best Practices

### 1. Performance
- Use caching for repeated operations
- Implement batch processing for large datasets
- Avoid unnecessary string concatenations

### 2. Memory Management
- Use generators for large text processing
- Implement proper cleanup for cached data
- Monitor memory usage during operations

### 3. Error Handling
- Always validate input strings
- Implement fallback mechanisms
- Log operation failures for debugging

### 4. Security
- Sanitize user input appropriately
- Validate string formats before processing
- Implement proper escaping for different contexts

## Troubleshooting

### Common Issues

1. **Memory Issues with Large Strings**
   ```python
   # Use generators for large text
   def process_large_text(file_path):
       with open(file_path, 'r') as f:
           for line in f:
               yield string_utils.clean_string(line)
   ```

2. **Unicode Handling**
   ```python
   # Normalize unicode before processing
   text = string_utils.normalize_unicode(input_text)
   cleaned = string_utils.clean_string(text)
   ```

3. **Performance with Regular Expressions**
   ```python
   # Compile regex patterns for reuse
   pattern = string_utils.compile_pattern(r'\d+')
   matches = string_utils.find_all(text, pattern)
   ```

## Conclusion

The string utilities in `siege_utilities` provide comprehensive tools for text processing and manipulation. By following this recipe, you can:

- Efficiently clean and normalize text data
- Implement robust string validation and sanitization
- Process large amounts of text with optimal performance
- Integrate string utilities into data pipelines and applications
- Handle errors gracefully with proper validation

Remember to always validate inputs, implement proper error handling, and use appropriate string operations for your specific use case.
