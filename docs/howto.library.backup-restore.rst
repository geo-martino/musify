Backup and restore your library data
====================================

In this example, you will:
   * Backup a local library to a JSON file
   * Restore tags for tracks from a JSON file backup
   * Backup a remote library to a JSON file
   * Restore remote playlists from a JSON file backup


.. include:: _howto/setup.logger.txt


Backup and restore a local library
----------------------------------

1. Load a local library. For more information on how to do this see :ref:`load-local`

   .. literalinclude:: _howto/scripts/local.library.load.py
      :language: Python
      :lines: 1-6

   .. literalinclude:: _howto/scripts/local.library.load.py
      :language: Python
      :lines: 12-24

2. Backup your library to JSON:

   .. literalinclude:: _howto/scripts/local.library.backup-restore.py
      :language: Python
      :lines: 4-8

3. Restore the tags for all tracks in your library from a JSON file:

   .. literalinclude:: _howto/scripts/local.library.backup-restore.py
      :language: Python
      :lines: 10-13

   ... or restore only a specific set of tags:

   .. literalinclude:: _howto/scripts/local.library.backup-restore.py
      :language: Python
      :lines: 15-27

4. Save the tags to the track files:

   .. literalinclude:: _howto/scripts/local.library.backup-restore.py
      :language: Python
      :lines: 29-30


Backup and restore a remote library
-----------------------------------

1. Load a remote library. For more information on how to do this see any of
   the relevant guides for loading remote libraries.

   Note:
      This step uses the ``SpotifyLibrary``, but any supported music streaming service
      can be used in generally the same way. Just modify the imports and classes as required.

   .. literalinclude:: _howto/scripts/spotify.api.py
      :language: Python

2. Backup your library to JSON:

   .. literalinclude:: _howto/scripts/spotify.library.backup-restore.py
      :language: Python
      :lines: 6-10

3. Restore the playlists in your library from a JSON file and sync the playlists:

   .. literalinclude:: _howto/scripts/spotify.library.backup-restore.py
      :language: Python
      :lines: 12-17
