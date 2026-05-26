"""
Hygiene utilities for maintaining siege_utilities package.

This module provides tools for package maintenance including:
- Documentation generation and management

For release management, use ``scripts/release_manager.py`` directly.
"""

from .generate_docstrings import main as generate_docstrings

__all__ = [
    'generate_docstrings',
]
