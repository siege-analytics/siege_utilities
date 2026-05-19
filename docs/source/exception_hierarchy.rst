Exception Hierarchy
===================

``siege_utilities`` follows a **fail-loud-over-silent-swallow** policy: when
a function cannot deliver its documented output, it raises a typed exception
rather than returning ``None``, ``False``, or an empty container that looks
like a legitimate "no result." This distinguishes real failures from
expected empty-input paths and prevents silent data corruption in
downstream pipelines.

This page catalogs the typed exceptions across the library. Every exception
subclasses a standard Python exception (``LookupError``, ``ValueError``,
``RuntimeError``) so broad existing handlers continue to work.

Design principles
-----------------

1. **Lookup failures are ``LookupError``.** Missing chart types, missing
   client configs, and similar "you asked for X but X doesn't exist" cases.
2. **Parameter / input failures are ``ValueError``.** Missing required
   parameters, invalid values, bad config shapes.
3. **Operation failures are ``RuntimeError``.** Failed I/O, failed parse,
   failed API call — anything where the inputs were valid but the work
   did not complete.
4. **Not-found return values are preserved where semantic.** ``list_X()``
   returning ``[]``, lookup helpers returning ``None`` when the caller
   should handle absence as normal — these are unchanged. The rewrite
   only affects sites where absence was *masking* a transport or parse
   failure.
5. **Every raise chains with ``from e``.** Inspect ``exc.__cause__`` to
   see the underlying error (``JSONDecodeError``, ``OSError``,
   ``HTTPError``, etc.).

Reporting
---------

Top-level config export / import
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoexception:: siege_utilities.reporting.ReportingConfigError
   :show-inheritance:

Chart type registry
~~~~~~~~~~~~~~~~~~~

.. autoexception:: siege_utilities.reporting.chart_types.UnknownChartTypeError
   :show-inheritance:

.. autoexception:: siege_utilities.reporting.chart_types.ChartParameterError
   :show-inheritance:

.. autoexception:: siege_utilities.reporting.chart_types.ChartCreationError
   :show-inheritance:

Client branding
~~~~~~~~~~~~~~~

.. autoexception:: siege_utilities.reporting.client_branding.ClientBrandingNotFoundError
   :show-inheritance:

.. autoexception:: siege_utilities.reporting.client_branding.ClientBrandingError
   :show-inheritance:

Geographic
----------

Census Bureau geocoder
~~~~~~~~~~~~~~~~~~~~~~

.. autoexception:: siege_utilities.geo.census_geocoder.CensusGeocodeError
   :show-inheritance:

Before this change, ``geocode_single()`` and ``geocode_batch()`` caught all
failures (network, API, parse) and returned
``CensusGeocodeResult(matched=False)``. Downstream pipelines treated
unmatched rows as "address not findable" and dropped them — so API
outages silently poisoned entire batches with fake unmatched rows.
``CensusGeocodeError`` surfaces the real cause.

Spatial data sources
~~~~~~~~~~~~~~~~~~~~

.. autoexception:: siege_utilities.geo.spatial_data.SpatialDataError
   :show-inheritance:

Used by ``GovernmentDataSource`` (CKAN-style portals) and
``OpenStreetMapDataSource`` (Overpass API). Distinct from boundary
retrieval, which has its own hierarchy below.

Boundary retrieval
~~~~~~~~~~~~~~~~~~

.. autoexception:: siege_utilities.geo.boundary_result.BoundaryRetrievalError
   :show-inheritance:

.. autoexception:: siege_utilities.geo.boundary_result.BoundaryInputError
   :show-inheritance:

.. autoexception:: siege_utilities.geo.boundary_result.BoundaryDiscoveryError
   :show-inheritance:

.. autoexception:: siege_utilities.geo.boundary_result.BoundaryUrlValidationError
   :show-inheritance:

.. autoexception:: siege_utilities.geo.boundary_result.BoundaryDownloadError
   :show-inheritance:

.. autoexception:: siege_utilities.geo.boundary_result.BoundaryParseError
   :show-inheritance:

.. autoexception:: siege_utilities.geo.boundary_result.BoundaryConfigurationError
   :show-inheritance:

Migration guidance
------------------

Callers that relied on the pre-rewrite silent-swallow behavior must
migrate to ``try/except`` around the new exception types.

Before::

    result = registry.create_chart("unknown_type")
    if result is None:
        log.warning("chart creation failed")
        return None

After::

    try:
        result = registry.create_chart("unknown_type")
    except UnknownChartTypeError:
        log.warning("unknown chart type")
        return None
    except ChartCreationError as e:
        log.error("chart creation failed: %s", e.__cause__)
        raise

Because the exception types subclass standard Python exceptions, you can
also use a single broad ``except LookupError:`` / ``except ValueError:`` /
``except RuntimeError:`` if you do not need to distinguish cases. The
``__cause__`` attribute still gives you the original error.

Further reading
---------------

* :doc:`../../docs/FAILURE_MODES` — complete anti-pattern catalog
* :doc:`../../docs/ARCHITECTURE` — three-layer dependency model
