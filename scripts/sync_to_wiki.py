#!/usr/bin/env python3
"""
Sync Siege Utilities Wiki Recipes to GitHub Wiki

This script helps synchronize wiki documentation from the wiki/
directory to a GitHub wiki repository for easier maintenance and sharing.

Usage:
    python scripts/sync_to_wiki.py --wiki-path /path/to/wiki/repo
    python scripts/sync_to_wiki.py --wiki-url https://github.com/username/repo.wiki.git
"""

import os
import sys
import shutil
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

def run_command(cmd, cwd=None, check=True):
    """Run a shell command and return the result"""
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            cwd=cwd, 
            capture_output=True, 
            text=True, 
            check=check
        )
        return result
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {e}")
        return e

def clone_wiki_repo(wiki_url, target_path):
    """Clone the wiki repository"""
    print(f"Cloning wiki repository from {wiki_url}")
    
    if os.path.exists(target_path):
        print(f"Target directory {target_path} already exists")
        return True
    
    result = run_command(f"git clone {wiki_url} {target_path}")
    return result.returncode == 0

def sync_wiki_to_wiki(wiki_source, wiki_path):
    """Sync wiki files to the wiki repository"""
    print(f"Syncing wiki content from {wiki_source} to {wiki_path}")
    
    # Copy all wiki files
    copied_files = []
    for root, dirs, files in os.walk(wiki_source):
        # Calculate relative path from wiki source
        rel_path = os.path.relpath(root, wiki_source)
        if rel_path == '.':
            wiki_target_dir = wiki_path
        else:
            wiki_target_dir = os.path.join(wiki_path, rel_path)
        
        # Create target directory
        os.makedirs(wiki_target_dir, exist_ok=True)
        
        # Copy markdown files
        for file in files:
            if file.endswith('.md'):
                source_file = os.path.join(root, file)
                target_file = os.path.join(wiki_target_dir, file)
                
                shutil.copy2(source_file, target_file)
                copied_files.append(target_file)
                print(f"  Copied: {file}")
    
    return copied_files

def update_wiki_index(wiki_path, copied_files):
    """Update the wiki index to include recipes"""
    index_file = os.path.join(wiki_path, "Home.md")
    
    # Create or update the index
    if not os.path.exists(index_file):
        index_content = """# Siege Utilities Wiki

Welcome to the Siege Utilities documentation and recipes wiki.

## Quick Links

- [Recipes](Recipes.md) - Practical examples and use cases
- [API Reference](https://siege-analytics.github.io/siege_utilities/) - Complete API documentation
- [GitHub Repository](https://github.com/siege-analytics/siege_utilities) - Source code and issues

## Getting Started

1. Install Siege Utilities: `pip install siege-utilities`
2. Check out the [Basic Setup](recipes/getting_started/basic_setup.md) recipe
3. Explore [File Operations](recipes/file_operations/batch_processing.md) examples
4. Learn [Distributed Computing](recipes/distributed_computing/spark_processing.md) workflows

## Contributing

To contribute recipes or documentation:
1. Fork the main repository
2. Add your recipe to the `docs/recipes/` directory
3. Submit a pull request
4. The recipe will be automatically synced to this wiki

---
*Last updated: {timestamp}*
"""
    else:
        # Read existing content and update recipes section
        with open(index_file, 'r') as f:
            content = f.read()
        
        # Simple update - add recipes section if not present
        if "## Recipes" not in content:
            recipes_section = """

## Recipes

- [Basic Setup](recipes/getting_started/basic_setup.md) - Install and configure Siege Utilities
- [Batch File Processing](recipes/file_operations/batch_processing.md) - Process multiple files efficiently
- [Spark Data Processing](recipes/distributed_computing/spark_processing.md) - Work with Apache Spark
- [Multi-Platform Analytics](recipes/analytics/multi_platform_collection.md) - Collect data from multiple platforms

"""
            # Insert before the last section
            if "## Contributing" in content:
                content = content.replace("## Contributing", recipes_section + "## Contributing")
            else:
                content += recipes_section
    
    # Update timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    content = content.replace("{timestamp}", timestamp)
    
    with open(index_file, 'w') as f:
        f.write(content)
    
    print(f"  Updated: {index_file}")

def commit_and_push_changes(wiki_path, commit_message=None):
    """Commit and push changes to the wiki repository"""
    if not commit_message:
        commit_message = f"Update recipes - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    print(f"Committing changes: {commit_message}")
    
    # Add all files
    run_command("git add .", cwd=wiki_path)
    
    # Commit
    result = run_command(f'git commit -m "{commit_message}"', cwd=wiki_path)
    if result.returncode != 0:
        print("No changes to commit")
        return False
    
    # Push
    result = run_command("git push origin main", cwd=wiki_path)
    if result.returncode == 0:
        print("Successfully pushed changes to wiki")
        return True
    else:
        print("Failed to push changes")
        return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Sync recipes to GitHub wiki")
    parser.add_argument(
        "--wiki-path", 
        help="Path to local wiki repository"
    )
    parser.add_argument(
        "--wiki-url", 
        help="URL of wiki repository to clone"
    )
    parser.add_argument(
        "--commit-message", 
        help="Custom commit message"
    )
    parser.add_argument(
        "--no-push", 
        action="store_true", 
        help="Don't push changes (just commit locally)"
    )
    
    args = parser.parse_args()
    
    # Determine wiki path
    if args.wiki_path:
        wiki_path = args.wiki_path
        if not os.path.exists(wiki_path):
            print(f"Error: Wiki path {wiki_path} does not exist")
            sys.exit(1)
    elif args.wiki_url:
        # Clone to a temporary directory
        wiki_path = f"temp_wiki_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        if not clone_wiki_repo(args.wiki_url, wiki_path):
            print("Failed to clone wiki repository")
            sys.exit(1)
    else:
        print("Error: Must specify either --wiki-path or --wiki-url")
        sys.exit(1)
    
    # Get wiki source path
    script_dir = Path(__file__).parent
    wiki_source = script_dir.parent / "wiki"
    
    if not wiki_source.exists():
        print(f"Error: Wiki source directory {wiki_source} does not exist")
        sys.exit(1)
    
    try:
        # Sync wiki content
        copied_files = sync_wiki_to_wiki(wiki_source, wiki_path)
        
        if not copied_files:
            print("No wiki recipe files found to sync")
            return
        
        # Update wiki index
        update_wiki_index(wiki_path, copied_files)
        
        # Commit changes
        if commit_and_push_changes(wiki_path, args.commit_message):
            print("✅ Successfully synced recipes to wiki")
        else:
            print("⚠️ Changes committed but push failed")
        
        # Cleanup temporary directory if we cloned it
        if args.wiki_url and os.path.exists(wiki_path):
            shutil.rmtree(wiki_path)
            print(f"Cleaned up temporary directory: {wiki_path}")
            
    except Exception as e:
        print(f"Error during sync: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
