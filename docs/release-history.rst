.. Add log for your proposed changes here.

   The versions shall be listed in descending order with the latest release first.

   Change categories:
      Added          - for new features.
      Changed        - for changes in existing functionality.
      Deprecated     - for soon-to-be removed features.
      Removed        - for now removed features.
      Fixed          - for any bug fixes.
      Security       - in case of vulnerabilities.
      Documentation  - for changes that only affected documentation and no functionality.

   Your additions should keep the same structure as observed throughout the file i.e.

      <release version>
      =================

      <one of the above change categories>
      ------------------------------------
      * <your 1st change>
      * <your 2nd change>
      ...

.. _release-history:

===============
Release History
===============

The format is based on `Keep a Changelog <https://keepachangelog.com/en>`_.
This project adheres to a modified `Calendar Versioning <https://calver.org/>`_ i.e. ``YYYY-M-P`` where

* ``YYYY`` = The current year
* ``M`` = The current month
* ``P`` = An 0-indexed incrementing index for the release version for this month


2024.1.4
========

Documentation
-------------

* Expanded docstrings across entire package


2024.1.3
========

Changed
-------

* Removed x10 factor on bar threshold on _get_items_multi function in SpotifyAPI

Fixed
-----

* LocalTrack would break when trying to save tags for unmapped tag names, now handles correctly


2024.1.2
========

Fixed
-----

* MusifyLogger would not get file_paths for parent loggers when propagate == True, now it does


2024.1.1
========

Changed
-------

* Remove automatic assignment of absolute path to package root for relative paths on CurrentTimeRotatingFileHandler

Fixed
-----

* CurrentTimeRotatingFileHandler now creates dirs for new log directories


2024.1.0
========

Added
-----

Initial release! 🎉