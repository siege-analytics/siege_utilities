import os
import sys
sys.path.insert(0, os.path.abspath('../../'))

project = 'Siege Utilities'
copyright = '2025, Dheeraj Chand'
author = 'Dheeraj Chand'
release = '1.0.0'

# Minimal extensions for fast builds
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
]

# Disable all heavy processing
autodoc_default_options = {
    'members': False,
    'undoc-members': False,
    'show-inheritance': False,
    'imported-members': False,
}

# Performance optimizations
autodoc_mock_imports = ['pyspark', 'geopy', 'pandas', 'numpy', 'sqlalchemy']
autodoc_typehints = 'none'
autodoc_class_signature = 'separated'

# Disable viewcode (slow)
viewcode_follow_imports = False

# Basic theme
html_theme = 'sphinx_rtd_theme'
html_theme_options = {
    'sticky_navigation': True,
    'navigation_depth': 2,
    'collapse_navigation': False,
    'titles_only': False,
}

# Build performance settings
html_copy_source = False
html_show_sourcelink = False
html_use_index = False

# Disable search (can be slow)
html_use_opensearch = False
