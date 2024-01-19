Get useful stats about your libraries
=====================================

In this example, you will:
   * Get stats on the differences in playlists between two libraries
   * Get stats on the missing tags in a local library


.. include:: _howto/setup.logging.txt


Report on differences in playlists
----------------------------------

1. Load two libraries. See other guides for more info on how to do this.

2. Run the report:

   .. literalinclude:: _howto/scripts/reports.py
      :language: Python
      :lines: 9-11


Report on missing tags
----------------------

1. Load a local library or collection of local objects. See other guides for more info on how to do this.

2. Run the report:

   .. literalinclude:: _howto/scripts/reports.py
      :language: Python
      :lines: 13-26
