Load and save tags to a local track
===================================

In this example, you will:
   * Load a local track
   * Modify the tags of a local track and save them to the file


.. include:: _howto/setup.logging.txt


Load a track
------------

Load a track as follows:

.. literalinclude:: _howto/scripts/local.track.load-save/p1.py
   :language: Python

You can also just have Musify automatically determine the track type to load based on the file's extension:

.. literalinclude:: _howto/scripts/local.track.load-save/p1_load.py
   :language: Python

If you want to be able to assign a URI to your track, you'll need to provide a :py:class:`.RemoteDataWrangler`
to the track object for the relevant music streaming source.

The following is an example for doing this with Spotify as the data source:

.. literalinclude:: _howto/scripts/local.track.load-save/p1_wrangler.py
   :language: Python


Modify the track's tags
-----------------------

.. note::
   To be able to modify a track's images, you will need to have installed the ``images`` optional dependencies.
   See :ref:`installation` for more details.

1. Change some tags:

   .. literalinclude:: _howto/scripts/local.track.load-save/p2.py
      :language: Python
      :lines: 3-

2. Save all the modified tags to the file:

   .. literalinclude:: _howto/scripts/local.track.load-save/p3_all.py
      :language: Python
      :lines: 3-

   ... or select exactly which modified tags you wish to save:

   .. literalinclude:: _howto/scripts/local.track.load-save/p3_tags.py
      :language: Python
      :lines: 3-
