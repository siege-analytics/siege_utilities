import os
import sys

sys.path.insert(0, os.path.abspath('../../'))

project = 'Siege Utilities'
copyright = '2025-2026, Dheeraj Chand'
author = 'Dheeraj Chand'
release = '3.24.0'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
]

autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'undoc-members': False,
    'show-inheritance': True,
    'imported-members': False,
}

autodoc_mock_imports = [
    'pyspark', 'geopy', 'pandas', 'numpy', 'sqlalchemy',
    'geopandas', 'shapely', 'fiona', 'pyproj', 'rtree',
    'django', 'rest_framework', 'osgeo', 'rasterio',
    'duckdb', 'sedona', 'tobler', 'osmnx', 'h3',
    'reportlab', 'pptx', 'plotly', 'matplotlib',
    'databricks', 'trino', 'snowflake',
    'pydantic', 'yaml', 'requests', 'tqdm',
    'scipy', 'openpyxl', 'pyarrow', 'faker',
    'folium', 'branca', 'seaborn', 'PIL',
    'mapclassify', 'censusgeocode', 'topojson',
    'google', 'facebook_business', 'datadotworld',
    'weightipy', 'keyring', 'boto3', 'hydra',
    'omegaconf', 'bs4', 'lxml', 's2sphere', 'h3',
    'psycopg', 'psycopg2', 'wkls', 'etter',
]
autodoc_typehints = 'description'
autodoc_class_signature = 'separated'

napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'pandas': ('https://pandas.pydata.org/docs/', None),
    'geopandas': ('https://geopandas.org/en/stable/', None),
    'shapely': ('https://shapely.readthedocs.io/en/stable/', None),
}

html_theme = 'sphinx_rtd_theme'
html_theme_options = {
    'sticky_navigation': True,
    'navigation_depth': 4,
    'collapse_navigation': False,
    'titles_only': False,
    'prev_next_buttons_location': 'bottom',
}
