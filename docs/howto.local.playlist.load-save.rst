Create, load, and update a local playlist
=========================================

In this example, you will:
   * Create a local playlist from scratch
   * Load a local playlist
   * Modify the tracks in a playlist and save the changes to the file


.. include:: _howto/setup.logging.txt


Create a playlist
-----------------

You can create a playlist as follows:

.. literalinclude:: _howto/scripts/local.playlist.load-save.py
   :language: Python
   :lines: 1-11

Load a playlist
---------------

You can load a playlist as follows:

.. note::
   To be able to use the XAutoPF playlist type, you will need to have installed the ``musicbee`` optional dependencies.
   See :ref:`installation` for more details.

.. literalinclude:: _howto/scripts/local.playlist.load-save.py
   :language: Python
   :lines: 13-17

You can also just have Musify automatically determine the playlist type to load based on the file's extension:

.. literalinclude:: _howto/scripts/local.playlist.load-save.py
   :language: Python
   :lines: 19-21

If you already have some tracks loaded, and you want the playlist to only use those tracks instead of loading
the tracks itself, you can pass these preloaded tracks to the playlist too.

.. literalinclude:: _howto/scripts/local.playlist.load-save.py
   :language: Python
   :lines: 23-32

There may also be cases where the files in the file need mapping to be loaded e.g. if the paths
contained in the playlist file are relative paths.
You may give the playlist object a :py:class:`.PathMapper` or :py:class:`.PathStemMapper` to handle this.

.. literalinclude:: _howto/scripts/local.playlist.load-save.py
   :language: Python
   :lines: 34-36

If you want to be able to read/update URIs on the loaded tracks,
you'll need to provide a :py:class:`.RemoteDataWrangler`
to the playlist object for the relevant music streaming source.

The following is an example for doing this with Spotify as the data source:

.. literalinclude:: _howto/scripts/local.playlist.load-save.py
   :language: Python
   :lines: 38-40


Modify the playlist
-------------------

1. Add some tracks to the playlist:

   .. literalinclude:: _howto/scripts/local.playlist.load-save.py
      :language: Python
      :lines: 42-47

2. Save the playlist:

   .. literalinclude:: _howto/scripts/local.playlist.load-save.py
      :language: Python
      :lines: 49-50
