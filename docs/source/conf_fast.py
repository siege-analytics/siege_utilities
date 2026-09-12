import os
import sys

sys.path.insert(0, os.path.abspath('../../'))

project = 'Siege Utilities'
copyright = '2025-2026, Dheeraj Chand'
author = 'Dheeraj Chand'
release = '3.24.0'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
]

autodoc_default_options = {
    'members': False,
    'undoc-members': False,
    'show-inheritance': False,
    'imported-members': False,
}

autodoc_mock_imports = [
    'pyspark', 'geopy', 'pandas', 'numpy', 'sqlalchemy',
    'geopandas', 'shapely', 'fiona', 'pyproj', 'rtree',
    'django', 'rest_framework', 'osgeo', 'rasterio',
    'duckdb', 'sedona', 'tobler', 'osmnx', 'h3',
    'reportlab', 'pptx', 'plotly', 'matplotlib',
    'databricks', 'trino', 'snowflake',
    'pydantic', 'yaml', 'requests',
]
autodoc_typehints = 'none'
autodoc_class_signature = 'separated'

napoleon_google_docstring = True
napoleon_numpy_docstring = True

html_theme = 'sphinx_rtd_theme'
html_theme_options = {
    'sticky_navigation': True,
    'navigation_depth': 2,
    'collapse_navigation': False,
    'titles_only': False,
}

html_copy_source = False
html_show_sourcelink = False
html_use_index = False
