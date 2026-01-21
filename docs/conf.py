import os
import sys
sys.path.insert(0, os.path.abspath('../'))

project = 'Siege Utilities'
copyright = '2025, Dheeraj Chand'
author = 'Dheeraj Chand'
release = '1.0.0'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
]

html_theme = 'sphinx_rtd_theme'
html_title = 'Siege Utilities Documentation'