siege_utilities.files.paths
===========================

.. py:module:: siege_utilities.files.paths


Attributes
----------

.. autoapisummary::

   siege_utilities.files.paths.logger


Functions
---------

.. autoapisummary::

   siege_utilities.files.paths.ensure_path_exists
   siege_utilities.files.paths.unzip_file_to_its_own_directory


Module Contents
---------------

.. py:function:: ensure_path_exists(desired_path: pathlib.Path) -> pathlib.Path

   """
   Perform file operations: ensure path exists.

   Part of Siege Utilities File Operations module.
   Auto-discovered and available at package level.

   :returns: Description needed

   .. rubric:: Example

   >>> import siege_utilities
   >>> result = siege_utilities.ensure_path_exists()
   >>> print(result)

   .. note::

      This function is auto-discovered and available without imports
      across all siege_utilities modules.

   """


.. py:function:: unzip_file_to_its_own_directory(path_to_zipfile: pathlib.Path, new_dir_name=None, new_dir_parent=None)

   """
   Perform file operations: unzip file to its own directory.

   Part of Siege Utilities File Operations module.
   Auto-discovered and available at package level.

   :returns: Description needed

   .. rubric:: Example

   >>> import siege_utilities
   >>> result = siege_utilities.unzip_file_to_its_own_directory()
   >>> print(result)

   .. note::

      This function is auto-discovered and available without imports
      across all siege_utilities modules.

   """


.. py:data:: logger

