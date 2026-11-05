Hygiene
=======

Data cleaning and validation: docstring generation, code quality.

Docstring generation
--------------------

Preview missing docstrings without modifying source files::

    python -m siege_utilities.hygiene.generate_docstrings --path .

Apply the additions explicitly after reviewing the preview::

    python -m siege_utilities.hygiene.generate_docstrings --path . --write

``--apply`` is an alias for ``--write``; ``--dry-run`` explicitly selects the
default preview mode. Python callers must pass ``dry_run=False`` to
``process_python_file`` or ``main`` to write files. This replaces the previous
write-by-default behavior.

The generator inserts docstring lines into public synchronous and asynchronous
functions, preserving existing comments, formatting, encoding, and line endings.
One-line suites are skipped with a warning because adding docstring lines would
require reformatting their existing source. Existing docstrings are left intact.
Directory exclusions match whole path components, including ``build``, ``dist``,
caches, ``.git``, and Django ``migrations`` directories. Names such as
``distributed``, ``redistricting``, and ``builds`` remain eligible.

Generated templates use signature information without importing target modules.
Examples carry ``# doctest: +SKIP`` because names may not be package exports and
calls may require external resources. Review the descriptions for domain-specific
meaning before committing them.

.. automodule:: siege_utilities.hygiene
   :members:
   :show-inheritance:

Submodules
----------

.. automodule:: siege_utilities.hygiene.generate_docstrings
   :members:
   :show-inheritance:
