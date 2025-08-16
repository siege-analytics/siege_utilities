#!/bin/bash

# Release Manager Script Wrapper
# Makes it easy to manage releases from command line

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Function to show usage
show_usage() {
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  check                    Check version consistency across platforms"
    echo "  bump [major|minor|patch] Bump version in setup.py"
    echo "  build                    Build Python package"
    echo "  upload-pypi              Upload package to PyPI"
    echo "  release [type] [notes]   Perform full release process"
    echo "  help                     Show this help message"
    echo ""
    echo "Release Types:"
    echo "  major                    Major version bump (x.0.0)"
    echo "  minor                    Minor version bump (x.y.0)"
    echo "  patch                    Patch version bump (x.y.z)"
    echo ""
    echo "Examples:"
    echo "  $0 check                                    # Check versions"
    echo "  $0 bump minor                               # Bump minor version"
    echo "  $0 build                                    # Build package"
    echo "  $0 release minor 'New features added'       # Full release"
    echo ""
    echo "Environment Variables:"
    echo "  GITHUB_TOKEN              GitHub API token for releases"
    echo "  PYPI_TOKEN                PyPI API token for uploads"
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

# Function to check environment
check_environment() {
    if [[ -z "$GITHUB_TOKEN" ]]; then
        echo "Warning: GITHUB_TOKEN not set, GitHub releases will be skipped"
    fi
    
    if [[ -z "$PYPI_TOKEN" ]]; then
        echo "Warning: PYPI_TOKEN not set, PyPI uploads will be skipped"
    fi
}

# Function to run release manager
run_release_manager() {
    echo "Starting Release Manager..."
    echo "Project root: $PROJECT_ROOT"
    echo ""
    
    python3 "$SCRIPT_DIR/release_manager.py" "$@"
}

# Main script logic
main() {
    # Check dependencies
    check_dependencies
    
    # Check environment
    check_environment
    
    # Parse command
    if [[ $# -eq 0 ]]; then
        show_usage
        exit 1
    fi
    
    case "$1" in
        "check")
            run_release_manager --check
            ;;
        "bump")
            if [[ -z "$2" ]]; then
                echo "Error: bump requires version type (major|minor|patch)"
                exit 1
            fi
            run_release_manager --bump "$2"
            ;;
        "build")
            run_release_manager --build
            ;;
        "upload-pypi")
            run_release_manager --upload-pypi
            ;;
        "release")
            if [[ -z "$2" || -z "$3" ]]; then
                echo "Error: release requires type and notes"
                echo "Usage: $0 release [major|minor|patch] 'Release notes'"
                exit 1
            fi
            run_release_manager --release --bump-type "$2" --release-notes "$3"
            ;;
        "help"|"-h"|"--help")
            show_usage
            ;;
        *)
            echo "Error: Unknown command '$1'"
            show_usage
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
