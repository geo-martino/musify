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

2024.1.6
========

Fixed
-----

* Rename __max_str in local/collection.py to _max_str - functions could not see variable
* Add default value of 0 to sort_key in ItemSorter.sort_by_field
* Fixed RemoteItemChecker _pause logic to only get playlist name when input is not False-y


2024.1.5
========

Added
-----

* Add the ItemDownloadHelper general processor

Changed
-------

* Factor out logging handlers to their own script to avoid circular import issues
* Abstract away input methods of RemoteItemChecker to InputProcessor base class
* Factor out patch_input method to function in InputProcessor derived tests

Fixed
-----

* Captured stdout assertions in RemoteItemChecker tests re-enabled, now fixed
* Surround RemoteApi 'user' properties in try-except block so they can still be
  pretty printed even if API is not authorised

Documentation
-------------

* Fix redirect/broken links
* Change notes text to proper rst syntax


2024.1.4
========

Fixed
-----

* Fix bug in ``restore_tracks`` method on library due to 'images' tag name not being present in track properties

Documentation
-------------

* Expand docstrings across entire package
* Expand documentation with how to section, release history, and contributions pages


2024.1.3
========

Changed
-------

* Remove x10 factor on bar threshold on _get_items_multi function in SpotifyAPI

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
