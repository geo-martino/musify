Load a Spotify library and objects
==================================

In this example, you will:
   * Authorise access to the `Spotify Web API <https://developer.spotify.com/documentation/web-api>`_
   * Load your Spotify library
   * Load some other Spotify objects
   * Add some tracks to a playlist


.. include:: setup.logging.txt


Set up the Spotify API
----------------------

1. If you don't already have one, create a `Spotify for Developers <https://developer.spotify.com/dashboard>`_ account.

2. If you don't already have one, `create an app <https://developer.spotify.com/documentation/web-api/concepts/apps>`_.
   Select "Web API" when asked which APIs you are planning on using.
   To use this program, you will only need to take note of the **client ID** and **client secret**.

3. Create a :py:class:`.SpotifyAPI` object and authorise the program access to Spotify data as follows:

   .. note::
      The scopes listed in this example will allow access to read your library data and write to your playlists.
      See Spotify Web API documentation for more information about
      `scopes <https://developer.spotify.com/documentation/web-api/concepts/scopes>`_

   .. literalinclude:: scripts/spotify.api.py
      :language: Python


Load your library
-----------------

1. Define helper functions for loading your library data:

   .. literalinclude:: scripts/spotify.load/p1.py
      :language: Python
      :lines: 3-

2. Define helper functions for loading some Spotify objects using any of the supported identifiers:

   .. literalinclude:: scripts/spotify.load/p2.py
      :language: Python
      :lines: 3-

3. Define helper function for adding some tracks to a playlist in your library, synchronising with Spotify,
   and logging the results:

   .. literalinclude:: scripts/spotify.load/p3.py
      :language: Python
      :lines: 3-

4. Run the program:

   .. literalinclude:: scripts/spotify.load/p99.py
      :language: Python
      :lines: 3-
