Load and save tags to a local track
===================================

In this example, you will:
   * Load a local track
   * Modify the tags of a local track and save them to the file


.. include:: _howto/setup.logging.txt


Load a track
------------

You can load a track as follows:

.. literalinclude:: _howto/scripts/local.track.load-save.py
   :language: Python
   :lines: 1-9

You can also just have Musify automatically determine the track type to load based on the file's extension:

.. literalinclude:: _howto/scripts/local.track.load-save.py
   :language: Python
   :lines: 11-13

If you want to be able to assign a URI to your track, you'll need a give the provide a ``RemoteDataWrangler``
to the track object for the relevant music streaming source.

The following is an example for doing this with Spotify as the data source:

.. literalinclude:: _howto/scripts/local.track.load-save.py
   :language: Python
   :lines: 15-17


Modify the track's tags
-----------------------

1. Change some tags:

   .. literalinclude:: _howto/scripts/local.track.load-save.py
      :language: Python
      :lines: 19-36

2. Save the tags to the file:

   .. literalinclude:: _howto/scripts/local.track.load-save.py
      :language: Python
      :lines: 38-57
