import os
import sys

sys.path.insert(0, os.path.abspath('../../'))

project = 'Siege Utilities'
copyright = '2025, Dheeraj Chand'
author = 'Dheeraj Chand'
release = '1.0.0'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
    'autoapi.extension',
]

# AutoAPI settings - comprehensive documentation
autoapi_dirs = ['../../siege_utilities']
autoapi_root = 'api'
autoapi_add_toctree_entry = False
autoapi_generate_api_docs = True
autoapi_python_class_content = 'both'
autoapi_member_order = 'groupwise'
autoapi_keep_files = True

# Autodoc settings
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__',
    'show-inheritance': True,
}

# Napoleon settings for docstrings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_use_admonition_for_examples = True
napoleon_use_admonition_for_notes = True

html_theme = 'sphinx_rtd_theme'
html_theme_options = {
    'canonical_url': '',
    'analytics_id': '',
    'display_version': True,
    'prev_next_buttons_location': 'bottom',
    'style_external_links': False,
    'collapse_navigation': False,
    'sticky_navigation': True,
    'navigation_depth': 4,
    'includehidden': True,
    'titles_only': False
}

# Auto-generate summary tables
autosummary_generate = True


def setup(app):
    """Custom setup to auto-generate function lists."""
    try:
        import siege_utilities

        # Generate comprehensive function list
        info = siege_utilities.get_package_info()
        functions_by_module = {}

        # Group functions by their source module
        for func_name in info.get('available_functions', []):
            func_info = siege_utilities.get_function_info(func_name)
            if func_info:
                module = func_info.get('module', 'unknown')
                if module not in functions_by_module:
                    functions_by_module[module] = []
                functions_by_module[module].append(func_name)

        # Generate RST file with all functions
        with open('source/all_functions.rst', 'w') as f:
            f.write("Complete Function Reference\n")
            f.write("===========================\n\n")
            f.write(
                f"Siege Utilities contains {len(info.get('available_functions', []))} auto-discovered functions.\n\n")

            for module, functions in sorted(functions_by_module.items()):
                f.write(f"{module}\n")
                f.write("-" * len(module) + "\n\n")
                for func in sorted(functions):
                    f.write(f".. autofunction:: siege_utilities.{func}\n\n")

        print(f"✅ Generated comprehensive function documentation")

    except Exception as e:
        print(f"⚠️  Could not auto-generate function lists: {e}")