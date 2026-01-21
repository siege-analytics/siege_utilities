siege_utilities.files.operations
================================

.. py:module:: siege_utilities.files.operations


Attributes
----------

.. autoapisummary::

   siege_utilities.files.operations.logger


Functions
---------

.. autoapisummary::

   siege_utilities.files.operations.check_for_file_type_in_directory
   siege_utilities.files.operations.check_if_file_exists_at_path
   siege_utilities.files.operations.count_duplicate_rows_in_file_using_awk
   siege_utilities.files.operations.count_empty_rows_in_file_pythonically
   siege_utilities.files.operations.count_empty_rows_in_file_using_awk
   siege_utilities.files.operations.count_total_rows_in_file_pythonically
   siege_utilities.files.operations.count_total_rows_in_file_using_sed
   siege_utilities.files.operations.delete_existing_file_and_replace_it_with_an_empty_file
   siege_utilities.files.operations.remove_empty_rows_in_file_using_sed
   siege_utilities.files.operations.rmtree
   siege_utilities.files.operations.write_data_to_a_new_empty_file
   siege_utilities.files.operations.write_data_to_an_existing_file


Module Contents
---------------

.. py:function:: check_for_file_type_in_directory(target_file_path: pathlib.Path, file_type: str) -> bool

   :param target_file_path:
   :param file_type:
   :return: bool


.. py:function:: check_if_file_exists_at_path(target_file_path: pathlib.Path) -> bool

   :param target_file_path: This is the path we are going to check to see if a file exists
   :return: True if file exists, False otherwise


.. py:function:: count_duplicate_rows_in_file_using_awk(target_file_path: pathlib.Path) -> int

   "This uses an awk pattern from Justin Hernandez to count duplicate rows in file"
   :param target_file_path: pathlib.Path object that we are going to count the duplicate rows of
   :return: count of duplicate rows in file


.. py:function:: count_empty_rows_in_file_pythonically(target_file_path: pathlib.Path) -> int

   :param target_file_path: pathlib.Path object that we are going to count the empty rows of
   :return: count of empty rows in file


.. py:function:: count_empty_rows_in_file_using_awk(target_file_path: pathlib.Path) -> int

   :param target_file_path: pathlib.Path object that we are going to count the empty rows of
   :return: count of empty rows in file


.. py:function:: count_total_rows_in_file_pythonically(target_file_path: pathlib.Path) -> int

   :param target_file_path: pathlib.Path object that we are going to count the rows of
   :return: count of total rows in file


.. py:function:: count_total_rows_in_file_using_sed(target_file_path: pathlib.Path) -> int

   :param target_file_path: pathlib.Path object that we are going to count the total rows of
   :return: count of total rows in file


.. py:function:: delete_existing_file_and_replace_it_with_an_empty_file(target_file_path: pathlib.Path) -> pathlib.Path

   This function deletes the existing file and replaces it with an empty file.
   :param target_file_path: Pathlib.path object to interact with
   :return: pathlib.Path object to interact with


.. py:function:: remove_empty_rows_in_file_using_sed(target_file_path: pathlib.Path, fixed_file_path: pathlib.Path = None)

   :param target_file_path: pathlib.Path object that we are going to remove the empty rows of
   :param target_file_path: pathlib.Path object to path for saved fixed file
   :return:


.. py:function:: rmtree(f: pathlib.Path)

   """
   Utility function: rmtree.

   Part of Siege Utilities Utilities module.
   Auto-discovered and available at package level.

   :returns: Description needed

   .. rubric:: Example

   >>> import siege_utilities
   >>> result = siege_utilities.rmtree()
   >>> print(result)

   .. note::

      This function is auto-discovered and available without imports
      across all siege_utilities modules.

   """


.. py:function:: write_data_to_a_new_empty_file(target_file_path: pathlib.Path, data: str) -> pathlib.Path

   :param target_file_path: file path to write data to
   :param data: what to write
   :return: the path to the file


.. py:function:: write_data_to_an_existing_file(target_file_path: pathlib.Path, data: str) -> pathlib.Path

   :param target_file_path: file path to write data to
   :param data: what to write
   :return: the path to the file


.. py:data:: logger

