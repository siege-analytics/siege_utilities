siege_utilities.files.hashing
=============================

.. py:module:: siege_utilities.files.hashing

.. autoapi-nested-parse::

   Hash Management Functions - Fixed Version
   Provides standardized hash functions that actually exist and work properly



Functions
---------

.. autoapisummary::

   siege_utilities.files.hashing.calculate_file_hash
   siege_utilities.files.hashing.generate_sha256_hash_for_file
   siege_utilities.files.hashing.get_file_hash
   siege_utilities.files.hashing.get_quick_file_signature
   siege_utilities.files.hashing.test_hash_functions
   siege_utilities.files.hashing.verify_file_integrity


Module Contents
---------------

.. py:function:: calculate_file_hash(file_path) -> Optional[str]

   Alias for get_file_hash with SHA256 - for backward compatibility


.. py:function:: generate_sha256_hash_for_file(file_path) -> Optional[str]

   Generate SHA256 hash for a file - chunked reading for large files

   :param file_path: Path to the file (str or Path object)

   :returns: SHA256 hash as hexadecimal string, or None if error


.. py:function:: get_file_hash(file_path, algorithm='sha256') -> Optional[str]

   Generate hash for a file using specified algorithm

   :param file_path: Path to the file (str or Path object)
   :param algorithm: Hash algorithm to use ('sha256', 'md5', 'sha1', etc.)

   :returns: Hash as hexadecimal string, or None if error


.. py:function:: get_quick_file_signature(file_path) -> str

   Generate a quick file signature using file stats + partial hash
   Faster for change detection, not cryptographically secure

   :param file_path: Path to the file

   :returns: Quick signature string


.. py:function:: test_hash_functions()

   Test the hash functions with a temporary file


.. py:function:: verify_file_integrity(file_path, expected_hash, algorithm='sha256') -> bool

   Verify file integrity by comparing with expected hash

   :param file_path: Path to the file
   :param expected_hash: Expected hash value
   :param algorithm: Hash algorithm used

   :returns: True if file matches expected hash, False otherwise


