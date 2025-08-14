#!/bin/bash

# Simple wrapper script for the documentation automation
# This script provides easy access to common automation workflows

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  docs          Generate documentation and update wikis"
    echo "  deploy        Full deployment workflow (docs + git + push)"
    echo "  test          Run tests and quality checks only"
    echo "  wiki          Update wiki repositories only"
    echo "  status        Update branch status only"
    echo "  help          Show this help message"
    echo ""
    echo "Options:"
    echo "  --dry-run     Run without making actual changes"
    echo "  --skip-tests  Skip running tests"
    echo "  --force       Force execution even with warnings"
    echo "  --config      Use custom configuration file"
    echo ""
    echo "Examples:"
    echo "  $0 docs --dry-run                    # Generate docs in dry-run mode"
    echo "  $0 deploy --skip-tests               # Deploy without running tests"
    echo "  $0 wiki                              # Update wikis only"
    echo "  $0 status                            # Update branch status only"
}

# Function to check if Python script exists
check_python_script() {
    local script_path="scripts/automate_docs_and_deploy.py"
    if [[ ! -f "$script_path" ]]; then
        print_error "Python automation script not found: $script_path"
        exit 1
    fi
}

# Function to run the Python script
run_automation() {
    local args=("$@")
    local script_path="scripts/automate_docs_and_deploy.py"
    
    print_status "Running automation script with args: ${args[*]}"
    python3 "$script_path" "${args[@]}"
}

# Main script logic
main() {
    # Check if we're in the right directory
    if [[ ! -f "setup.py" ]] && [[ ! -d "siege_utilities" ]]; then
        print_error "Please run this script from the project root directory"
        exit 1
    fi
    
    # Check if Python script exists
    check_python_script
    
    # Parse command
    case "${1:-help}" in
        "docs")
            print_status "Generating documentation and updating wikis..."
            run_automation "${@:2}"
            ;;
        "deploy")
            print_status "Running full deployment workflow..."
            run_automation "${@:2}"
            ;;
        "test")
            print_status "Running tests and quality checks..."
            run_automation --skip-tests "${@:2}"
            ;;
        "wiki")
            print_status "Updating wiki repositories..."
            run_automation --skip-tests "${@:2}"
            ;;
        "status")
            print_status "Updating branch status..."
            run_automation --skip-tests "${@:2}"
            ;;
        "help"|"-h"|"--help")
            show_usage
            ;;
        *)
            print_error "Unknown command: $1"
            show_usage
            exit 1
            ;;
    esac
}

# Check if help is requested
if [[ "$1" == "help" ]] || [[ "$1" == "-h" ]] || [[ "$1" == "--help" ]]; then
    show_usage
    exit 0
fi

# Run main function with all arguments
main "$@"
