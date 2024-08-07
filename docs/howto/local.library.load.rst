.. _load-local:

Load a local library and objects
================================

In this example, you will:
   * Load a local library including tracks, playlists, and other local objects


.. include:: setup.logging.txt


Create a library object
-----------------------

You can create one of any of the supported local library types for this guide as follows:

* Generic local library

   .. literalinclude:: scripts/local.library.load/p0_local.py
      :language: Python

* MusicBee

   .. note::
      To be able to use a MusicBee library, you will need to have installed the ``musicbee`` optional dependencies.
      See :ref:`installation` for more details.

   .. literalinclude:: scripts/local.library.load/p0_musicbee.py
      :language: Python


Load your library and other objects
-----------------------------------

1. Load your library:

   .. literalinclude:: scripts/local.library.load/p1.py
      :language: Python
      :lines: 3-

2. Get collections from your library:

   .. literalinclude:: scripts/local.library.load/p2.py
      :language: Python
      :lines: 3-

3. Get a track from your library using any of the following identifiers:

   .. literalinclude:: scripts/local.library.load/p3.py
      :language: Python
      :lines: 3-
