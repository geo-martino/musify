Create a playlist of your followed artists' latest music
========================================================

In this example, you will:
   * Load information about your followed artists
   * Load the tracks released by these artists between two dates
   * Create a playlist containing these tracks


.. include:: _howto/setup.logger.txt


Create the playlist
-------------------

1. Create a remote library object:

   Note:
      This step uses the ``SpotifyLibrary``, but any supported music streaming service
      can be used in generally the same way. Just modify the imports and classes as required.

   .. literalinclude:: _howto/scripts/spotify.api.py
      :language: Python

2. Load data about your followed artists:

   .. literalinclude:: _howto/scripts/remote.new-music.py
      :language: Python
      :lines: 6-7

3. Define the date range you wish to get track for and define this helper function for filtering albums:

   .. literalinclude:: _howto/scripts/remote.new-music.py
      :language: Python
      :lines: 9-23

4. Filter the albums and load the tracks for only these albums:

   .. literalinclude:: _howto/scripts/remote.new-music.py
      :language: Python
      :lines: 26-39

5. Create a new playlist and add these tracks:

   .. literalinclude:: _howto/scripts/remote.new-music.py
      :language: Python
      :lines: 41-51
