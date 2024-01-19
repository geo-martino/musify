.. _load-local:

Load a local library and objects
================================

In this example, you will:
   * Load a local library including tracks, playlists, and other local objects


.. include:: _howto/setup.logger.txt


Create a library object
-----------------------

You can create one of any of the supported local library types for this guide as follows:

* Generic local library

   .. literalinclude:: _howto/scripts/local.library.load.py
      :language: Python
      :lines: 1-6

* MusicBee

   .. literalinclude:: _howto/scripts/local.library.load.py
      :language: Python
      :lines: 8-10


Load your library and other objects
-----------------------------------

1. Load your library:

   .. literalinclude:: _howto/scripts/local.library.load.py
      :language: Python
      :lines: 12-24

2. Get collections from your library:

   .. literalinclude:: _howto/scripts/local.library.load.py
      :language: Python
      :lines: 26-33

3. Get a track from your library using any of the following identifiers:

   .. literalinclude:: _howto/scripts/local.library.load.py
      :language: Python
      :lines: 38-46
