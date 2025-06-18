siege_utilities.hygiene.generate_docstrings
===========================================

.. py:module:: siege_utilities.hygiene.generate_docstrings

.. autoapi-nested-parse::

   Auto-generate docstrings for functions missing them in siege_utilities.
   Part of the hygiene maintenance toolkit.



Attributes
----------

.. autoapisummary::

   siege_utilities.hygiene.generate_docstrings.success


Classes
-------

.. autoapisummary::

   siege_utilities.hygiene.generate_docstrings.DocstringAdder


Functions
---------

.. autoapisummary::

   siege_utilities.hygiene.generate_docstrings.analyze_function_signature
   siege_utilities.hygiene.generate_docstrings.categorize_function
   siege_utilities.hygiene.generate_docstrings.cli
   siege_utilities.hygiene.generate_docstrings.find_python_files
   siege_utilities.hygiene.generate_docstrings.generate_docstring_template
   siege_utilities.hygiene.generate_docstrings.main
   siege_utilities.hygiene.generate_docstrings.process_python_file


Module Contents
---------------

.. py:class:: DocstringAdder(module_name='unknown')

   Bases: :py:obj:`ast.NodeTransformer`


   AST transformer to add docstrings to functions.


   .. py:method:: visit_FunctionDef(node)

      Visit Functiondef.

      General utility functions.
      Auto-discovered function available at package level.

      :returns: Description needed
      :rtype: Any

      .. rubric:: Example

      >>> import siege_utilities
      >>> result = siege_utilities.visit_FunctionDef()
      >>> # Process result as needed

      .. note::

         This function is auto-discovered and available without imports
         across all siege_utilities modules.



   .. py:attribute:: functions_processed
      :value: 0



   .. py:attribute:: functions_skipped
      :value: 0



   .. py:attribute:: module_name
      :value: 'unknown'



.. py:function:: analyze_function_signature(func)

   Analyze a function to generate parameter and return type info.


.. py:function:: categorize_function(func_name)

   Categorize function based on name patterns.


.. py:function:: cli()

   Command line interface.


.. py:function:: find_python_files(base_path)

   Find all Python files to process.


.. py:function:: generate_docstring_template(func_name, func_obj=None)

   Generate a comprehensive docstring template.


.. py:function:: main()

   Main function to process all Python files in siege_utilities.


.. py:function:: process_python_file(file_path)

   Process a single Python file to add missing docstrings.


.. py:data:: success
   :value: False


