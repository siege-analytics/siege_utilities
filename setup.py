from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="siege-utilities",
    version="1.0.0",
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
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.25.0",
        "tqdm>=4.60.0",
    ],
    extras_require={
        "distributed": ["pyspark>=3.0.0"],
        "geo": ["geopy>=2.0.0"],
        "dev": ["pytest>=6.0.0", "black>=21.0.0", "flake8>=3.8.0"],
    },
)