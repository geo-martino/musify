Load a Spotify library and objects
==================================

In this example, you will:
   * Authorise access to the `Spotify Web API <https://developer.spotify.com/documentation/web-api>`_
   * Load your Spotify library
   * Load some other Spotify objects
   * Add some tracks to a playlist


.. include:: _howto/setup.logging.txt


Setup the Spotify API
---------------------

1. If you don't already have one, create a `Spotify for Developers <https://developer.spotify.com/dashboard/login>`_ account.

2. If you don't already have one, `create an app <https://developer.spotify.com/documentation/web-api/concepts/apps>`_.
   Select "Web API" when asked which APIs you are planning on using.
   To use this program, you will only need to take note of the **client ID** and **client secret**.

3. Create a ``SpotifyAPI`` object and authorise the program access to Spotify data as follows:

   **NOTE:**
   The scopes listed in this example will allow access to read your library data and write to your playlists.
   See Spotify Web API documentation for more information about [scopes](https://developer.spotify.com/documentation/web-api/concepts/scopes)

   .. literalinclude:: _howto/scripts/spotify.api.py
      :language: Python


Load your library
-----------------

1. Create a ``SpotifyLibrary`` object and load your library data as follows:

   .. literalinclude:: _howto/scripts/spotify.load.py
      :language: Python
      :lines: 4-30

2. Load some Spotify objects using any of the supported identifiers as follows:

   .. literalinclude:: _howto/scripts/spotify.load.py
      :language: Python
      :lines: 32-49

3. Add some tracks to a playlist in your library, synchronise with Spotify, and log the results as follows:

   **NOTE**: This step will only work if you chose to load either your playlists or your entire library in step 4.

   .. literalinclude:: _howto/scripts/spotify.load.py
      :language: Python
      :lines: 51-62
