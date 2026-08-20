"""Third-party library integrations.

Each subpackage wraps a specific external library, exposing a siege-native
interface (``ConnectorProtocol``-shaped, ``pandas.DataFrame``-returning,
``ConnectorError``-raising) so consumers don't have to import from the
wrapped library directly.

Current subpackages:

- :mod:`siege_utilities.integrations.parsons` — TMC Parsons wrappers.

See ``docs/PARSONS_LICENSE_ANALYSIS.md`` and ``docs/PARSONS_DEP_MATRIX.md``
for the integration boundaries.
"""
