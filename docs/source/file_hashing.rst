File Hashing
============

The file hashing module provides utilities for generating various types of file hashes and checksums for data integrity verification.

Module Overview
--------------

.. automodule:: siege_utilities.files.hashing
   :members:
   :undoc-members:
   :show-inheritance:

Functions
---------

.. autofunction:: siege_utilities.files.hashing.calculate_md5
   :noindex:

.. autofunction:: siege_utilities.files.hashing.calculate_sha1
   :noindex:

.. autofunction:: siege_utilities.files.hashing.calculate_sha256
   :noindex:

.. autofunction:: siege_utilities.files.hashing.calculate_file_hash
   :noindex:

.. autofunction:: siege_utilities.files.hashing.verify_file_integrity
   :noindex:

Usage Examples
-------------

Basic file hashing:

.. code-block:: python

   import siege_utilities
   
   # Calculate MD5 hash
   md5_hash = siege_utilities.calculate_md5('document.pdf')
   print(f"MD5: {md5_hash}")
   
   # Calculate SHA256 hash
   sha256_hash = siege_utilities.calculate_sha256('document.pdf')
   print(f"SHA256: {sha256_hash}")
   
   # Calculate SHA1 hash
   sha1_hash = siege_utilities.calculate_sha1('document.pdf')
   print(f"SHA1: {sha1_hash}")

Generic hashing with algorithm selection:

.. code-block:: python

   # Use generic hash function
   hash_value = siege_utilities.calculate_file_hash('data.csv', algorithm='sha256')
   print(f"Hash: {hash_value}")
   
   # Available algorithms: md5, sha1, sha256, sha512
   algorithms = ['md5', 'sha1', 'sha256']
   hashes = {}
   
   for algo in algorithms:
       hashes[algo] = siege_utilities.calculate_file_hash('large_file.dat', algorithm=algo)
   
   for algo, hash_val in hashes.items():
       print(f"{algo.upper()}: {hash_val}")

File integrity verification:

.. code_block:: python

   # Verify file integrity
   original_hash = "a1b2c3d4e5f6..."
   is_valid = siege_utilities.verify_file_integrity('document.pdf', original_hash, 'sha256')
   
   if is_valid:
       print("File integrity verified!")
   else:
       print("File may be corrupted or modified")

Batch processing:

.. code_block:: python

   import os
   
   # Process multiple files
   files_to_hash = ['file1.txt', 'file2.txt', 'file3.txt']
   hash_results = {}
   
   for filename in files_to_hash:
       if os.path.exists(filename):
           hash_results[filename] = {
               'md5': siege_utilities.calculate_md5(filename),
               'sha256': siege_utilities.calculate_sha256(filename)
           }
   
   # Display results
   for filename, hashes in hash_results.items():
       print(f"\n{filename}:")
       print(f"  MD5: {hashes['md5']}")
       print(f"  SHA256: {hashes['sha256']}")

Unit Tests
----------

The file hashing module has comprehensive test coverage:

.. code_block:: text

   ✅ test_file_hashing.py - All file hashing tests pass
   
   Test Coverage:
   - MD5 hash calculation
   - SHA1 hash calculation
   - SHA256 hash calculation
   - Generic hash function with algorithm selection
   - File integrity verification
   - Error handling for missing files
   - Performance with large files
   - Hash consistency across multiple calls

Test Results: All file hashing tests pass successfully with comprehensive coverage.
