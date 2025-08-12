import os
import sys
sys.path.insert(0, os.path.abspath('../../'))

project = 'Siege Utilities'
copyright = '2025, Dheeraj Chand'
author = 'Dheeraj Chand'
release = '1.0.0'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    # 'autoapi.extension',  # Temporarily disabled for faster builds
]

# AutoAPI settings (disabled for performance)
# autoapi_dirs = ['../../siege_utilities']
# autoapi_root = 'api'
# autoapi_add_toctree_entry = False
# autoapi_generate_api_docs = True
# autoapi_member_order = 'groupwise'
# autoapi_keep_files = True

# Autodoc settings (optimized for performance)
autodoc_default_options = {
    'members': False,  # Disable member generation for speed
    'member-order': 'bysource',
    'undoc-members': False,  # Disable undocumented members
    'show-inheritance': False,  # Disable inheritance diagrams
    'imported-members': False,  # Disable imported member processing
}

# Performance optimizations
autodoc_mock_imports = ['pyspark', 'geopy', 'pandas', 'numpy', 'sqlalchemy']
autodoc_typehints = 'none'  # Disable type hint processing
autodoc_class_signature = 'separated'  # Faster class signature processing

napoleon_google_docstring = True
napoleon_numpy_docstring = True

html_theme = 'sphinx_rtd_theme'
html_theme_options = {
    'sticky_navigation': True,
    'navigation_depth': 4,
    'collapse_navigation': False,
    'titles_only': False,
    'prev_next_buttons_location': 'bottom',
}

# Build performance settings
html_copy_source = False  # Don't copy source files
html_show_sourcelink = False  # Don't show source links
html_use_index = False  # Disable index generation