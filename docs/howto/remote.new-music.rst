Create a playlist of your followed artists' latest music
========================================================

In this example, you will:
   * Load information about your followed artists
   * Load the tracks released by these artists between two dates
   * Create a playlist containing these tracks


.. include:: setup.logging.txt


Create the playlist
-------------------

1. Create a :py:class:`.RemoteAPI` object:

   .. note::
      This step uses the :py:class:`.SpotifyLibrary`, but any supported music streaming service
      can be used in generally the same way. Just modify the imports and classes as required.

   .. literalinclude:: scripts/spotify.api.py
      :language: Python

2. If you haven't already, you will need to load and enrich data about your followed artists.
   You may use this helper function to help do so:

   .. literalinclude:: scripts/remote.new-music/p2.py
      :language: Python
      :lines: 3-

3. Define helper function for filtering albums:

   .. literalinclude:: scripts/remote.new-music/p3.py
      :language: Python
      :lines: 3-

4. Define helper function for filtering the albums and loading the tracks for only these albums:

   .. literalinclude:: scripts/remote.new-music/p4.py
      :language: Python
      :lines: 3-

5. Define driver function for creating the playlist:

   .. literalinclude:: scripts/remote.new-music/p5.py
      :language: Python
      :lines: 3-

5. Define the required parameters and run the operation:

   .. literalinclude:: scripts/remote.new-music/p99.py
      :language: Python
      :lines: 3-
