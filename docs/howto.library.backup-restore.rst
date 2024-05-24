Backup and restore your library data
====================================

In this example, you will:
   * Backup a local library to a JSON file
   * Restore tags for tracks from a JSON file backup
   * Backup a remote library to a JSON file
   * Restore remote playlists from a JSON file backup


.. include:: _howto/setup.logging.txt


Backup and restore a local library
----------------------------------

1. Load a local library. For more information on how to do this see :ref:`load-local`

   .. literalinclude:: _howto/scripts/local.library.load/p0_local.py
      :language: Python

   .. literalinclude:: _howto/scripts/local.library.load/p0_musicbee.py
      :language: Python

2. Backup your library to JSON:

   .. literalinclude:: _howto/scripts/local.library.backup-restore/p1.py
      :language: Python
      :lines: 3-

3. Restore the tags for all tracks in your library from a JSON file:

   .. literalinclude:: _howto/scripts/local.library.backup-restore/p2.py
      :language: Python
      :lines: 3-

   ... or restore only a specific set of tags:

   .. literalinclude:: _howto/scripts/local.library.backup-restore/p3.py
      :language: Python
      :lines: 3-

4. Save the tags to the track files:

   .. literalinclude:: _howto/scripts/local.library.backup-restore/p4.py
      :language: Python
      :lines: 3-


Backup and restore a remote library
-----------------------------------

1. Load a remote library. For more information on how to do this see any of
   the relevant guides for loading remote libraries.

   .. note::
      This step uses the :py:class:`.SpotifyLibrary`, but any supported music streaming service
      can be used in generally the same way. Just modify the imports and classes as required.

   .. literalinclude:: _howto/scripts/spotify.api.py
      :language: Python

2. Backup your library to JSON:

   .. literalinclude:: _howto/scripts/spotify.library.backup-restore/p1.py
      :language: Python
      :lines: 3-

3. Restore the playlists in your library from a JSON file and sync the playlists:

   .. literalinclude:: _howto/scripts/spotify.library.backup-restore/p2.py
      :language: Python
      :lines: 3-
