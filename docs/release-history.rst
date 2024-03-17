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


0.9.0
=====

Added
-----

* :py:class:`.RemoteAPI` methods now accept :py:class:`.RemoteResponse` objects as input, refreshing them automatically

Changed
-------

* :py:meth:`.LocalLibrary.load_tracks` and :py:meth:`.LocalLibrary.load_playlists` now run concurrently.
* Made :py:func:`.load_tracks` and :py:func:`.load_playlists` utility functions more DRY
* Move :py:meth:`.TagReader.load` from :py:class:`.LocalTrack` to super class :py:class:`.TagReader`
* Major refactoring and restructuring to local and remote modules to add composition

0.8.1
=====

Changed
-------

* :py:class:`.ItemSorter` now accepts ``shuffle_weight`` between -1 and 1 instead of 0 and 1.
  This parameter's logic has not yet been implemented so no changes to functionality have been made yet.
* Move :py:meth:`.get_filepaths` from :py:class:`.LocalTrack` to super class :py:class:`.File`

Documentation
-------------

* References to python objects now link correctly

Fixed
-----

* Comments from :py:class:`.LocalTrack` metadata loading no longer gets wiped after setting URI on init
* Tweaked assignment of description of IDv3 comment tags for :py:class:`.MP3`
* :py:func:`.align_string` function now handles combining unicode characters properly for fixed-width fonts
* :py:meth:`.LocalTrack.get_filepaths` on LocalTrack no longer returns paths from ``$RECYCLE.BIN`` folders.
  These are deleted files and were causing the package to crash when trying to load them.
* :py:meth:`.PrettyPrinter.json` and :py:meth:`.PrettyPrinter._to_str` converts attribute keys to string
  to ensure safe json/str/repr output
* :py:class:`.FilterMatcher` and :py:class:`.FilterComparers` now correctly import conditions from XML playlist files.
  Previously, these filters could not import nested match conditions from files.
  Changes to logic also made to :py:meth:`.Comparer.from_xml` to accommodate.
* :py:class:`.XMLLibraryParser` now handles empty arrays correctly. Previously would crash.
* Fixed :py:class:`.Comparer` dynamic process method alternate names for ``in_the_last`` and ``not_in_the_last``

Removed
-------

* Abstract uri.setter method on :py:class:`.Item`


0.8.0
=====

Added
-----

* Add debug log for error failure reason when loading tracks

Changed
-------

* Generating folders for a :py:class:`.LocalLibrary` now uses folder names
  as relative to the library folders of the :py:class:`.LocalLibrary`.
  This now supports nested folder structures better.
* Writing date tags to :py:class:`.LocalTrack` now supports partial dates of only YYYY-MM.
* Writing date tags to :py:class:`.LocalTrack` skips writing year, month, day tags if date tag already written.

Removed
-------

* set_compilation_tags method removed from :py:class:`.LocalFolder`.
  This contained author specific logic and was not appropriate for general use.

Fixed
-----

* ConnectionError catch in :py:class:`.RequestHandler` now handles correctly
* Added safe characters and replacements for path conversion in MusicBee :py:class:`.XMLLibraryParser`.
  Now converts path to expected XML format correctly.
* :py:class:`.FilterMatcher` now handles '&' character correctly.
* :py:class:`.SpotifyAPI` now only requests batches of up to 20 items when getting albums.
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
* Add default value of 0 to sort_key in :py:meth:`.ItemSorter.sort_by_field`
* Fixed :py:class:`.RemoteItemChecker` :py:meth:`._pause` logic to only get playlist name when input is not False-y


0.7.5
=====

Added
-----

* Add the :py:class:`.ItemDownloadHelper` general processor

Changed
-------

* Factor out logging handlers to their own script to avoid circular import issues
* Abstract away input methods of :py:class:`.RemoteItemChecker` to :py:class:`.InputProcessor` base class
* Factor out patch_input method to function in :py:class:`.InputProcessor` derived tests

Fixed
-----

* Captured stdout assertions in :py:class:`.RemoteItemChecker` tests re-enabled, now fixed
* Surround :py:class:`.RemoteAPI` 'user' properties in try-except block so they can still be
  pretty printed even if API is not authorised

Documentation
-------------

* Fix redirect/broken links
* Change notes text to proper rst syntax


0.7.4
=====

Fixed
-----

* Fix bug in :py:meth:`.LocalLibrary.restore_tracks` method on library
  due to 'images' tag name not being present in track properties

Documentation
-------------

* Expand docstrings across entire package
* Expand documentation with how to section, release history, and contributions pages


0.7.3
=====

Changed
-------

* Remove x10 factor on bar threshold on _get_items_multi function in :py:class:`.SpotifyAPI`

Fixed
-----

* :py:class:`.LocalTrack` would break when trying to save tags for unmapped tag names, now handles correctly


0.7.2
=====

Fixed
-----

* :py:class:`.MusifyLogger` would not get file_paths for parent loggers when propagate == True, now it does


0.7.1
=====

Changed
-------

* Remove automatic assignment of absolute path to package root
  for relative paths on :py:class:`.CurrentTimeRotatingFileHandler`

Fixed
-----

* :py:class:`.CurrentTimeRotatingFileHandler` now creates dirs for new log directories


0.7.0
=====

Added
-----

Initial release! 🎉
