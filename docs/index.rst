==================
Welcome to Musify!
==================

A Swiss Army knife for music library management
-----------------------------------------------

Helping you to manage your local and music streaming service (remote) libraries.

Features
--------

* Extract data for all item types from remote libraries, including following/saved items,
  such as: playlists, tracks, albums, artists, users, podcasts, audiobooks
* Load local audio files, programmatically manipulate, and save tags/metadata/embedded images
* Synchronise local tracks metadata with its matching track's metadata on supported music streaming services
* Synchronise local playlists with playlists on supported music streaming services
* Backup and restore track tags/metadata and playlists for local and remote libraries
* Extract and save images from remote tracks or embedded in local tracks

What's in this documentation
----------------------------

* How to guides on getting started with Musify and other key functionality of the package
* Release history
* How to get started with contributing to Musify
* Reference documentation

.. _installation:

Installation
------------

Install through pip using one of the following commands:

.. code-block:: bash

   pip install musify
   # or
   python -m pip install musify

This package has various optional dependencies for optional functionality.
Should you wish to take advantage of some or all of this functionality, install the optional dependencies as follows:

.. code-block:: bash

   pip install musify[all]  # installs all optional dependencies

   pip install musify[bars]  # dependencies for displaying progress bars on longer running processes
   pip install musify[images]  # dependencies for processing images
   pip install musify[musicbee]  # dependencies for working with a local MusicBee library and its playlist types
   pip install musify[sqlite]  # dependencies for working with a SQLite cache backend for caching API responses

   # or you may install any combination of these e.g.
   pip install musify[bars,images,musicbee]

.. toctree::
   :maxdepth: 1
   :caption: 📜 How to...

   howto.local.library.load
   howto.local.playlist.load-save
   howto.local.track.load-save
   howto.spotify.load
   howto.library.backup-restore
   howto.sync
   howto.remote.new-music
   howto.reports

.. toctree::
   :maxdepth: 2
   :caption: 🛠️ Project Info

   release-history
   contributing

.. toctree::
   :maxdepth: 1
   :caption: 📖 Reference

   musify.api
   musify.core
   musify.file
   musify.libraries
   musify.log
   musify.processors
   musify.exception
   musify.field
   musify.report
   musify.types
   musify.utils

   genindex
