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

The format is based on `Keep a Changelog <https://keepachangelog.com/en>`_,
and this project adheres to `Semantic Versioning <https://semver.org/spec/v2.0.0.html>`_


0.8.1
=====

Fixed
-----

* Comments from LocalTrack metadata loading no longer gets wiped after setting URI on init
* Tweaked description of IDv3 tag for MP3

Removed
-------

* Abstract uri.setter method on `Item`


0.8.0
=====

Added
-----

* Add debug log for error failure reason when loading tracks

Changed
-------

* Generating folders for a LocalLibrary now uses folder names as relative to the library folders of the LocalLibrary.
  This now supports nested folder structures better.
* Writing date tags to LocalTrack now supports partial dates of only YYYY-MM.
* Writing date tags to LocalTrack skips writing year, month, day tags if date tag already written.

Removed
-------

* set_compilation_tags method removed from LocalFolder.
  This contained author specific logic and was not appropriate for general use.

Fixed
-----

* ConnectionError catch in RequestHandler now handles correctly
* Added safe characters and replacements for path conversion in MusicBee XMLLibraryParser.
  Now converts path to expected XML format correctly.
* FilterMatcher now handles '&' character correctly.
* SpotifyAPI now only requests batches of up to 20 items when getting albums.
  Now matches Spotify Web API specifications better.
* Loading of logging yaml config uses UTF-8 encoding now
* Removed dependency on pytest-lazy-fixture.
  Package is `broken for pytest >8.0 <https://github.com/TvoroG/pytest-lazy-fixture/issues/65>`_.
  Replaced functionality with forked version of code.


0.7.6
=====

Fixed
-----

* Rename __max_str in local/collection.py to _max_str - functions could not see variable
* Add default value of 0 to sort_key in ItemSorter.sort_by_field
* Fixed RemoteItemChecker _pause logic to only get playlist name when input is not False-y


0.7.5
=====

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


0.7.4
=====

Fixed
-----

* Fix bug in ``restore_tracks`` method on library due to 'images' tag name not being present in track properties

Documentation
-------------

* Expand docstrings across entire package
* Expand documentation with how to section, release history, and contributions pages


0.7.3
=====

Changed
-------

* Remove x10 factor on bar threshold on _get_items_multi function in SpotifyAPI

Fixed
-----

* LocalTrack would break when trying to save tags for unmapped tag names, now handles correctly


0.7.2
=====

Fixed
-----

* MusifyLogger would not get file_paths for parent loggers when propagate == True, now it does


0.7.1
=====

Changed
-------

* Remove automatic assignment of absolute path to package root for relative paths on CurrentTimeRotatingFileHandler

Fixed
-----

* CurrentTimeRotatingFileHandler now creates dirs for new log directories


0.7.0
=====

Added
-----

Initial release! 🎉
