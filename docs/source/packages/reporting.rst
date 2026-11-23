Reporting
=========

Output generation: charts, PDFs, PowerPoint, hex cartograms, 3D maps, branded
multi-client reports.

.. automodule:: siege_utilities.reporting
   :members:
   :show-inheritance:

Charts and Visualization
------------------------

.. automodule:: siege_utilities.reporting.chart_generator
   :members:
   :show-inheritance:

.. automodule:: siege_utilities.reporting.chart_types
   :members:
   :show-inheritance:

.. automodule:: siege_utilities.reporting.wave_charts
   :members:
   :show-inheritance:

.. automodule:: siege_utilities.reporting.legend_manager
   :members:
   :show-inheritance:

.. automodule:: siege_utilities.reporting.image_utils
   :members:
   :show-inheritance:

Chart Engines
-------------

.. automodule:: siege_utilities.reporting.engines
   :members:
   :show-inheritance:

.. automodule:: siege_utilities.reporting.engines.base_engine
   :members:
   :show-inheritance:

.. automodule:: siege_utilities.reporting.engines.bar_engine
   :members:
   :show-inheritance:

.. automodule:: siege_utilities.reporting.engines.composite_engine
   :members:
   :show-inheritance:

.. automodule:: siege_utilities.reporting.engines.map_engine
   :members:
   :show-inheritance:

.. automodule:: siege_utilities.reporting.engines.stats_engine
   :members:
   :show-inheritance:

Reports and Documents
---------------------

``SocialMediaReportGenerator`` and ``AnalyticsReportGenerator`` write PDFs
under their ``output_dir`` and return a ``pathlib.Path`` after rendering
succeeds. Each call uses a unique filename derived from the report title.
The PDFs include collected metrics, tables, insights and charts.
The social-media facade produces PDF only; PowerPoint generation is available
separately through ``PowerPointGenerator``.

``create_website_performance_report`` selects the requested metric names from
the input dictionary (or its ``metrics`` dictionary) and includes optional
``executive_summary``, ``charts``, ``tables`` and ``insights`` payload fields.
``create_custom_analytics_report`` accepts a DataFrame, a dictionary, a JSON
string, or a CSV path according to ``data_source``. Set ``report_config['title']``
to customize its PDF title.

.. automodule:: siege_utilities.reporting.report_generator
   :members:
   :show-inheritance:

.. automodule:: siege_utilities.reporting.analytics_reports
   :members:
   :show-inheritance:

.. automodule:: siege_utilities.reporting.social_media_reports
   :members:
   :show-inheritance:

.. automodule:: siege_utilities.reporting.powerpoint_generator
   :members:
   :show-inheritance:

.. automodule:: siege_utilities.reporting.idml_export
   :members:
   :show-inheritance:

.. automodule:: siege_utilities.reporting.client_branding
   :members:
   :show-inheritance:

Analytics Reports
-----------------

.. automodule:: siege_utilities.reporting.analytics
   :members:
   :show-inheritance:

.. automodule:: siege_utilities.reporting.analytics.analytics_reports
   :members:
   :show-inheritance:

.. automodule:: siege_utilities.reporting.analytics.polling_analyzer
   :members:
   :show-inheritance:

Hex Cartograms
--------------

.. automodule:: siege_utilities.reporting.hex_cartogram
   :members:
   :show-inheritance:

.. automodule:: siege_utilities.reporting.hex_cartogram.algorithms
   :members:
   :show-inheritance:

.. automodule:: siege_utilities.reporting.hex_cartogram.components
   :members:
   :show-inheritance:

.. automodule:: siege_utilities.reporting.hex_cartogram.coords
   :members:
   :show-inheritance:

.. automodule:: siege_utilities.reporting.hex_cartogram.layouts
   :members:
   :show-inheritance:

.. automodule:: siege_utilities.reporting.hex_cartogram.renderer
   :members:
   :show-inheritance:

3D Maps
-------

.. automodule:: siege_utilities.reporting.map_3d
   :members:
   :show-inheritance:

Pages
-----

.. automodule:: siege_utilities.reporting.pages
   :members:
   :show-inheritance:

.. automodule:: siege_utilities.reporting.pages.page_models
   :members:
   :show-inheritance:
