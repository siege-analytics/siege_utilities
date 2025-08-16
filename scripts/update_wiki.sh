#!/bin/bash

# Wiki Update Script Wrapper
# Makes it easy to update the GitHub Wiki from command line

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --force          Force synchronization regardless of interval"
    echo "  --no-commit      Don't auto-commit changes"
    echo "  --auto-push      Auto-push changes to remote"
    echo "  --status         Show synchronization status"
    echo "  --config         Show current configuration"
    echo "  --help           Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                    # Normal sync (auto-commit, no auto-push)"
    echo "  $0 --force            # Force sync now"
    echo "  $0 --auto-push        # Sync and push to remote"
    echo "  $0 --status           # Check sync status"
    echo "  $0 --config           # Show configuration"
}

# Function to check dependencies
check_dependencies() {
    if ! command -v python3 &> /dev/null; then
        echo "Error: python3 is required but not installed"
        exit 1
    fi
    
    if ! command -v git &> /dev/null; then
        echo "Error: git is required but not installed"
        exit 1
    fi
}

# Function to run the update
run_update() {
    echo "Starting Wiki Update System..."
    echo "Project root: $PROJECT_ROOT"
    echo ""
    
    python3 "$SCRIPT_DIR/update_wiki.py" "$@"
}

# Main script logic
main() {
    # Check dependencies
    check_dependencies
    
    # Parse arguments
    if [[ $# -eq 0 ]]; then
        # No arguments, run normal sync
        run_update
    elif [[ "$1" == "--help" || "$1" == "-h" ]]; then
        show_usage
    else
        # Pass all arguments to the Python script
        run_update "$@"
    fi
}

# Run main function with all arguments
main "$@"
