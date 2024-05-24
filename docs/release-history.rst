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

1.0.0
=====

Added
-----

* Custom API caching backend to replace dependency on ``requests-cache`` package.
  Currently only supports SQLite backend. More backends can be implemented in future if desired.
* Cache settings for specific `GET` request endpoints on :py:class:`.SpotifyAPI` replacing need
  for per method ``use_cache`` parameter.
* The following classes should now be run as AsyncContextManagers to function correctly:
   * :py:class:`.SQLiteTable` & :py:class:`.SQLiteCache`
   * :py:class:`.RequestHandler`
   * :py:class:`.CachedSession`
   * :py:class:`.RemoteAPI` & :py:class:`.SpotifyAPI`

Changed
-------

* :py:class:`.RequestHandler` now handles requests asynchronously. These changes to async calls have
  been implemented all the way on :py:class:`.RemoteAPI` and all other objects that depend on it.
* Dependency injection pattern for :py:class:`.RequestHandler`.
  Now takes :py:class:`.APIAuthoriser` and generator for :py:class:`.ClientSession` objects for instantiation
  instead of kwargs for :py:class:`.APIAuthoriser`.
* Dependency injection pattern for :py:class:`.RemoteAPI`.
  Now takes :py:class:`.APIAuthoriser` and generator for :py:class:`.ResponseCache` objects for instantiation
  instead of kwargs for :py:class:`.APIAuthoriser`.
* :py:class:`.APIAuthoriser` kwargs given to :py:class:`.SpotifyAPI` now merge with default kwargs.
* Moved ``remote_wrangler`` attribute from :py:class:`.MusifyCollection` to :py:class:`.LocalCollection`.
  This attribute was only needed by :py:class:`.LocalCollection` branch of child classes.
* Moved ``logger`` attribute from :py:class:`.Library` to :py:class:`.RemoteLibrary`.
* Switch some dependencies to be optional for groups of operation: progress bars, images, musicbee, sqlite
* Replace urllib usages with ``yarl`` package.
* :py:class:`.SpotifyAPI` now logs to the new central :py:meth:`.RequestHandler.log` method
  to help unify log formatting.
* ``user_id`` and ``user_name`` now raise an error when called before setting ``user_data`` attribute.
  This is due to avoiding asynchronous calls in a property.
  It is therefore best to now enter the async context of the api to set these automatically.

Fixed
-----

* Added missing variables to __slots__ definitions
* Correctly applied __slots__ pattern to child classes. Now works as expected.
* :py:class:`.LocalTrack` now copies tags as expected when calling ``copy.copy()``
* Bug where loading an M3U playlist with new track objects would force all created track objects
  to have lower case paths
* :py:meth:`.RemoteLibrary.restore_playlists` now correctly handles the backup
  output from :py:meth:`.RemoteLibrary.backup_playlists`

Removed
-------

* Dependency on ``requests`` package in favour of ``aiohttp`` for async requests.
* Dependency on ``requests-cache`` package in favour of custom cache implementation.
* ``use_cache`` parameter from all :py:class:`.RemoteAPI` related methods.
  Cache settings now handled by :py:class:`.ResponseCache`
* ThreadPoolExecutor use on :py:class:`.RemoteItemSearcher`. Now uses asynchronous logic instead.

Documentation
-------------

* Updated how-to section to reflect changes to underlying code

0.9.2
=====

Added
-----

* ``REMOTE_SOURCES`` global variable in the ``libraries.remote`` module which lists the
  names of all the fully supported remote sources.
  Also, added the ``SOURCE_NAME`` global variable for the Spotify module.

Changed
-------

* :py:class:`.FilterComparers` now accepts a single :py:class:`.Comparer` on the ``comparers`` argument.
* :py:class:`.MusicBee` class attributes were renamed to classify that full paths are also valid, not just filenames.
* :py:class:`.ItemDownloadHelper` ``urls`` init arg now has default arg of empty tuple.

Documentation
-------------

* Fixed error in 'sync data' how-to.

Fixed
-----

* :py:class:`.Comparer` now considers strings as converted on first pass when converting expected values.
* Printing of new line at the end of :py:meth:`.RemoteLibrary.extend`

0.9.1
=====

Fixed
-----

* Bug in :py:meth:`.ItemMatcher.match` where operations always returned the last item in the given list of ``results``


0.9.0
=====

Added
-----

* :py:class:`.RemoteAPI` methods now accept :py:class:`.RemoteResponse` objects as input, refreshing them automatically
* Property 'kind' to all objects which have an associated :py:class:`.RemoteObjectType`
* Introduced :py:class:`.MusifyItemSettable` class to allow distinction
  between items that can have their properties set and those that can't
* Extend :py:class:`.FilterMatcher` with group_by tag functionality
* Now fully supports parsing of processors relating to :py:class:`.XAutoPF` objects with full I/O of settings
  to/from their related XML files on disk
* Now supports creating new :py:class:`.XAutoPF` files from scratch without the file needing to already exist
  For XML values not directly controlled by Musify, users can use the 'default_xml' class attribute
  to control the initial default values applied in this scenario
* 'length' property on :py:class:`.MusifyCollection` and implementation on all subclasses

Changed
-------

* Major refactoring and restructuring to all modules to improve modularity and add composition
* The following classes and methods have been modified to implement concurrency to improve performance:
   * :py:meth:`.LocalLibrary.load_tracks`
   * :py:meth:`.LocalLibrary.save_tracks`
   * :py:meth:`.LocalLibrary.load_playlists`
   * :py:meth:`.LocalLibrary.save_playlists`
   * :py:meth:`.LocalLibrary.json` + optimisation for extracting JSON data from tracks
   * :py:class:`.ItemMatcher`
   * :py:class:`.RemoteItemChecker`
   * :py:class:`.RemoteItemSearcher`
* Made :py:func:`.load_tracks` and :py:func:`.load_playlists` utility functions more DRY
* Move :py:meth:`.TagReader.load` from :py:class:`.LocalTrack` to super class :py:class:`.TagReader`
* :py:meth:`.SpotifyAPI.extend_items` now skips on responses that are already fully extended
* :py:meth:`.SpotifyArtist.load` now uses the base `load` method from :py:class:`.SpotifyCollectionLoader`
  meaning it now takes full advantage of the item filtering this method offers.
  As part of this, the base method was made more generic to accommodate all :py:class:`.SpotifyObject` types
* Renamed 'kind' property on :py:class:`.LocalTrack` to 'type' to avoid clashing property names
* :py:class:`.ItemMatcher`, :py:class:`.RemoteItemChecker`, and :py:class:`.RemoteItemSearcher` now accept
  all MusifyItem types that may have their URI property set manually
* :py:class:`.RemoteItemChecker` and :py:class:`.RemoteItemSearcher` no longer inherit from :py:class:`.ItemMatcher`.
  Composite pattern used instead.
* :py:class:`.ItemSorter` now shuffles randomly on unsupported types
  + prioritises fields settings over shuffle settings
* :py:meth:`.Comparer._in_range` now uses inclusive range i.e. ``a <= x <= b`` where ``x`` is the value to compare
  and ``a`` and ``b`` are the limits. Previously used exclusive range i.e. ``a < x < b``
* Removed ``from_xml`` and ``to_xml`` methods from all :py:class:`.MusicBeeProcessor` subclasses.
  Moved this logic to :py:class:`.XMLPlaylistParser` as distinct 'get' methods for each processor type
* Moved loading of XML file logic from :py:class:`.XAutoPF` to :py:class:`.XMLPlaylistParser`.
  :py:class:`.XMLPlaylistParser` is now solely responsible for all XML parsing and handling
  for :py:class:`.XAutoPF` files

Fixed
-----

* :py:class:`.Comparer` dynamic processor methods which process string values now cast expected types before processing

Removed
-------

* Redundant ShuffleBy enum and related arguments from :py:class:`.ItemSorter`
* ``ItemProcessor`` and ``MusicBeeProcessor`` abstraction layers. No longer needed after some refactoring
* ``get_filtered_playlists`` method from :py:class:`.Library`.
  This contained author specific logic and was not appropriate for general use

Documentation
-------------

* Added info on lint checking for the contributing page

0.8.1
=====

Changed
-------

* :py:class:`.ItemSorter` now accepts ``shuffle_weight`` between -1 and 1 instead of 0 and 1.
  This parameter's logic has not yet been implemented so no changes to functionality have been made yet
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
  These are deleted files and were causing the package to crash when trying to load them
* :py:meth:`.PrettyPrinter.json` and :py:meth:`.PrettyPrinter._to_str` converts attribute keys to string
  to ensure safe json/str/repr output
* :py:class:`.FilterMatcher` and :py:class:`.FilterComparers` now correctly import conditions from XML playlist files.
  Previously, these filters could not import nested match conditions from files.
  Changes to logic also made to :py:meth:`.Comparer.from_xml` to accommodate
* :py:class:`.XMLLibraryParser` now handles empty arrays correctly. Previously would crash
* Fixed :py:class:`.Comparer` dynamic process method alternate names for ``in_the_last`` and ``not_in_the_last``

Removed
-------

* Abstract uri.setter method on :py:class:`.Item`


0.8.0
=====

Added
-----

* Add debug log for error failure reason when loading tracks
* :py:meth:`.MusifyCollection.intersection` and :py:meth:`.MusifyCollection.difference` methods
* :py:meth:`.Playlist.merge` and :py:meth:`.Library.merge_playlists` methods

Changed
-------

* Generating folders for a :py:class:`.LocalLibrary` now uses folder names
  as relative to the library folders of the :py:class:`.LocalLibrary`.
  This now supports nested folder structures better
* Writing date tags to :py:class:`.LocalTrack` now supports partial dates of only YYYY-MM
* Writing date tags to :py:class:`.LocalTrack` skips writing year, month, day tags if date tag already written

Removed
-------

* set_compilation_tags method removed from :py:class:`.LocalFolder`.
  This contained author specific logic and was not appropriate for general use

Fixed
-----

* ConnectionError catch in :py:class:`.RequestHandler` now handles correctly
* Added safe characters and replacements for path conversion in MusicBee :py:class:`.XMLLibraryParser`.
  Now converts path to expected XML format correctly
* :py:class:`.FilterMatcher` now handles '&' character correctly
* :py:class:`.SpotifyAPI` now only requests batches of up to 20 items when getting albums.
  Now matches Spotify Web API specifications better
* Loading of logging yaml config uses UTF-8 encoding now
* Removed dependency on pytest-lazy-fixture.
  Package is `broken for pytest >8.0 <https://github.com/TvoroG/pytest-lazy-fixture/issues/65>`_.
  Replaced functionality with forked version of code


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
