Load and update a local playlist
================================

In this example, you will:
   * Load a local playlist
   * Modify the tracks in a playlist and save the changes to the file

Load a playlist
---------------

You can load a playlist as follows:

.. literalinclude:: _howto/scripts/local.playlist.load-save.py
   :language: Python
   :lines: 1-7

You can also just have Musify automatically determine the playlist type to load based on the file's extension:

.. literalinclude:: _howto/scripts/local.playlist.load-save.py
   :language: Python
   :lines: 9-11

If you already have some tracks loaded and you want the playlist to only use those tracks instead of loading
the tracks itself, you can pass these pre-loaded tracks to the playlist too.

.. literalinclude:: _howto/scripts/local.playlist.load-save.py
   :language: Python
   :lines: 15-22

There may also be cases where the files in the file need mapping to be loaded e.g. if the paths
contained in the playlist file are relative paths.
You may give the playlist object a ``PathMapper`` or ``PathStemMapper`` to handle this.

.. literalinclude:: _howto/scripts/local.playlist.load-save.py
   :language: Python
   :lines: 24-26

If you want to be able to read/update URIs on the loaded tracks, you'll need a give the provide a ``RemoteDataWrangler``
to the playlist object for the relevant music streaming source.

The following is an example for doing this with Spotify as the data source:

.. literalinclude:: _howto/scripts/local.playlist.load-save.py
   :language: Python
   :lines: 28-30

Modify the playlist
-------------------

1. Add some tracks to the playlist:

   .. literalinclude:: _howto/scripts/local.playlist.load-save.py
      :language: Python
      :lines: 32-37

2. Save the playlist:

   .. literalinclude:: _howto/scripts/local.playlist.load-save.py
      :language: Python
      :lines: 39-40
