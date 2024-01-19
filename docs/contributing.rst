============
Contributing
============
To contribute to Musify, follow these steps:


Setup your development environment
==================================
1. Ensure you have Python3.12 or greater installed on your system.
2. Go to the `GitHub repository <https://geo-martino.github.com/musify>`_ and fork the project by clicking
   **Fork** in the top left:

   .. image:: _images/contributing/musify_fork.png

3. Go to the page of your GitHub account's fork of Musify and
   `clone the repository <https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository>`_:

   .. image:: _images/contributing/musify_clone.png

4. In a terminal, navigate to the directory of the cloned project and create a virtual environment for Musify:

   .. code-block:: bash

      python -m venv .venv

5. Install the dependencies with ``pip`` for the changes you wish to make as follows:

   .. code-block:: bash

      pip install -e '.[test]'  # installs just the core package + the required dependencies for testing
      pip install -e '.[dev]'  # installs the `test` dependencies + dependencies for linting and other development uses
      pip install -e '.[docs]'  # installs just the core package + the required dependencies for building documentation


Making changes and testing
==========================
Create a new branch in your local git project and commit changes to this branch as you develop.

All tests are located within ``./tests``.
If you make any changes to the functionality of the package, you **must** either modify or add new tests for these changes.
To run tests, you must have installed either the ``test`` or ``dev`` optional dependencies and run ``pytest`` i.e.:

.. code-block:: bash

   pytest
   # OR
   pytest path/to/test/file.py


Submitting your changes for review
==================================
1. Ensure all tests pass locally first.
2. Add any changes you made to the :ref:`release-history`.
3. Go to your forked repository and open a pull request for your branch.

   .. image:: _images/contributing/musify_pr_new.png

   .. image:: _images/contributing/musify_pr_create1.png

4. Add a title, a motivation for your changes, and the changes you have made.
   This can just be a copy-paste from your release history notes.

   .. image:: _images/contributing/musify_pr_create2.png

5. Wait for a review and make any necessary changes.
6. Have your changes committed 🎉
