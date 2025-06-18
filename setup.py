from setuptools import setup, find_packages

setup(
    name="siege_utilities",
    version="1.0.0",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=["pathlib", "requests", "tqdm", "pandas", "tabulate"],
    extras_require={
        "distributed": ["pyspark"],
        "geo": ["geopy", "apache-sedona"],
        "dev": ["pytest", "black", "flake8"],
    },
)