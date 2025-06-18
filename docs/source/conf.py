import os
import sys
sys.path.insert(0, os.path.abspath('../../'))

# Project information
project = 'Siege Utilities'
copyright = '2025, Dheeraj Chand'
author = 'Dheeraj Chand'
release = '1.0.0'

# Extensions
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary', 
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
    'myst_parser',
]

# Settings
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'undoc-members': True,
    'show-inheritance': True,
}

autosummary_generate = True
napoleon_google_docstring = True

# Theme
html_theme = 'sphinx_rtd_theme'
html_theme_options = {
    'canonical_url': '',
    'analytics_id': '',
    'display_version': True,
    'prev_next_buttons_location': 'bottom',
    'style_navigation_bg': '#2980B9',
}

# Source files
source_suffix = {
    '.rst': None,
    '.md': 'myst_parser',
}

exclude_patterns = []
templates_path = ['_templates']
html_static_path = ['_static']