from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="siege-utilities",
    version="3.8.0",
    author="Dheeraj Chand",
    author_email="dheeraj@siegeanalytics.com",
    description="A comprehensive Python utilities package with enhanced auto-discovery",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/siege-analytics/siege_utilities",
    packages=find_packages(),  # Now this will work perfectly!
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.11",
    install_requires=[
        # Core dependencies only — synced with pyproject.toml [project.dependencies]
        "pyyaml>=6.0",
        "requests>=2.28.0",
        "tqdm>=4.60.0",
        "pydantic>=2.0.0",
    ],
    extras_require={
        "data": ["pandas>=1.5.0", "numpy>=1.21.0", "openpyxl>=3.1.0", "faker>=35.2.2"],
        "geo": [
            "geopandas>=0.13.2", "shapely>=1.8.0", "pyproj>=3.3.0", "fiona>=1.8.0",
            "geopy>=2.4.1", "rtree>=1.0.0", "mapclassify>=2.5.0", "tobler>=0.11.0",
            "osmnx>=1.9.4", "pysal>=24.1",
        ],
        "reporting": [
            "matplotlib>=3.7.5", "seaborn>=0.13.2", "folium>=0.18.0", "branca>=0.5.0",
            "plotly>=6.3.0", "reportlab>=4.4.3", "pypdf2>=3.0.1", "pillow>=10.0.0",
            "fonttools>=4.40.0",
        ],
        "analytics": [
            "google-auth>=2.40.3", "google-auth-oauthlib>=1.2.2",
            "google-auth-httplib2>=0.2.0", "google-api-python-client>=2.181.0",
            "google-analytics-data>=0.18.19", "google-analytics-admin>=0.25.0",
            "scipy>=1.8.0", "scikit-learn>=1.1.0",
            "facebook-business>=20.0.0", "datadotworld>=1.7.0",
            "snowflake-connector-python>=3.0.0",
        ],
        "distributed": ["pyspark>=3.3.0", "apache-sedona>=1.5.0"],
        "geodjango": [
            "django>=4.2.0", "djangorestframework>=3.14.0",
            "djangorestframework-gis>=1.0.0", "psycopg2-binary>=2.9.0",
        ],
        "config-extras": ["hydra-core>=1.3.0", "hydra-zen>=0.12.0", "omegaconf>=2.3.0"],
        "web": ["beautifulsoup4>=4.12.0", "lxml>=4.9.0"],
        "streamlit": [
            "streamlit>=1.28.0", "altair>=5.0.0", "bokeh>=3.0.0", "pydeck>=0.8.0",
            "ipywidgets>=8.0.0", "jupyter>=1.0.0", "notebook>=7.3.3",
        ],
        "export": ["openpyxl>=3.1.0", "xlsxwriter>=3.1.0", "psutil>=5.9.0", "memory-profiler>=0.61.0"],
        "performance": ["duckdb>=0.7.0"],
        "database": ["psycopg2-binary>=2.9.0", "sqlalchemy>=1.4.0"],
        "credentials": [],
        "dev": [
            "pytest>=7.0.0", "pytest-cov>=4.0.0", "pytest-mock>=3.10.0",
            "pytest-xdist>=3.0.0", "pytest-html>=3.1.0", "pytest-json-report>=1.5.0",
            "pytest-forked>=1.4.0", "black>=21.0.0", "flake8>=3.8.0",
            "astor>=0.8.1", "django>=4.2.0",
        ],
        "all": [
            # data
            "pandas>=1.5.0", "numpy>=1.21.0", "openpyxl>=3.1.0", "faker>=35.2.2",
            # geo
            "geopandas>=0.13.2", "shapely>=1.8.0", "pyproj>=3.3.0", "fiona>=1.8.0",
            "geopy>=2.4.1", "rtree>=1.0.0", "mapclassify>=2.5.0", "tobler>=0.11.0",
            "osmnx>=1.9.4", "pysal>=24.1",
            # reporting
            "matplotlib>=3.7.5", "seaborn>=0.13.2", "folium>=0.18.0", "branca>=0.5.0",
            "plotly>=6.3.0", "reportlab>=4.4.3", "pypdf2>=3.0.1", "pillow>=10.0.0",
            "fonttools>=4.40.0",
            # analytics
            "google-auth>=2.40.3", "google-auth-oauthlib>=1.2.2",
            "google-auth-httplib2>=0.2.0", "google-api-python-client>=2.181.0",
            "google-analytics-data>=0.18.19", "google-analytics-admin>=0.25.0",
            "scipy>=1.8.0", "scikit-learn>=1.1.0",
            "facebook-business>=20.0.0", "datadotworld>=1.7.0",
            "snowflake-connector-python>=3.0.0",
            # distributed
            "pyspark>=3.3.0", "apache-sedona>=1.5.0",
            # geodjango
            "django>=4.2.0", "djangorestframework>=3.14.0",
            "djangorestframework-gis>=1.0.0", "psycopg2-binary>=2.9.0",
            # config-extras
            "hydra-core>=1.3.0", "hydra-zen>=0.12.0", "omegaconf>=2.3.0",
            # web
            "beautifulsoup4>=4.12.0", "lxml>=4.9.0",
            # export
            "xlsxwriter>=3.1.0", "psutil>=5.9.0", "memory-profiler>=0.61.0",
            # performance
            "duckdb>=0.7.0",
            # database
            "sqlalchemy>=1.4.0",
            # streamlit (subset)
            "notebook>=7.3.3",
        ],
    },
)