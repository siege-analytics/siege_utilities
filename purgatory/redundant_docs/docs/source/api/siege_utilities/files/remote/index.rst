siege_utilities.files.remote
============================

.. py:module:: siege_utilities.files.remote


Attributes
----------

.. autoapisummary::

   siege_utilities.files.remote.logger


Functions
---------

.. autoapisummary::

   siege_utilities.files.remote.download_file
   siege_utilities.files.remote.generate_local_path_from_url


Module Contents
---------------

.. py:function:: download_file(url, local_filename)

   Download a file from a URL to a local file with progress bar

   :param url: The URL to download from
   :param local_filename: The local path where the file should be saved

   :returns: The local filename if successful, False otherwise


.. py:function:: generate_local_path_from_url(url: str, directory_path: pathlib.Path, as_string: bool = True)

   """
   Perform file operations: generate local path from url.

   Part of Siege Utilities File Operations module.
   Auto-discovered and available at package level.

   :returns: Description needed

   .. rubric:: Example

   >>> import siege_utilities
   >>> result = siege_utilities.generate_local_path_from_url()
   >>> print(result)

   .. note::

      This function is auto-discovered and available without imports
      across all siege_utilities modules.

   """


.. py:data:: logger

