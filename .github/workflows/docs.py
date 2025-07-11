name: Build and Deploy Documentation

on:
  push:
    branches: [main]

permissions:
  contents: read
  pages: write
  id-token: write

jobs:
  docs:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install sphinx sphinx-rtd-theme sphinx-autodoc-typehints myst-parser
        pip install sphinx-autoapi 
        pip install -e .

    - name: Build documentation
      run: |
        cd docs && make html

    - name: Setup Pages
      uses: actions/configure-pages@v4

    - name: Upload artifact
      uses: actions/upload-pages-artifact@v3
      with:
        path: './docs/build/html'

    - name: Deploy to GitHub Pages
      id: deployment
      uses: actions/deploy-pages@v4