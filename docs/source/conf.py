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
    'autoapi.extension',  # Re-enabled!
]

# AutoAPI settings
autoapi_dirs = ['../../siege_utilities']
autoapi_root = 'api'
autoapi_add_toctree_entry = False
autoapi_generate_api_docs = True
autoapi_member_order = 'groupwise'
autoapi_keep_files = True

# Autodoc settings
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'undoc-members': True,
    'show-inheritance': True,
}

napoleon_google_docstring = True
napoleon_numpy_docstring = True

html_theme = 'sphinx_rtd_theme'
html_theme_options = {
    'display_version': True,
    'prev_next_buttons_location': 'bottom',
    'collapse_navigation': False,
    'sticky_navigation': True,
    'navigation_depth': 4,
}