Sync data between local and remote libraries
============================================

In this example, you will:
   * Search for local tracks on a music streaming service and assign unique remote IDs to tags in your local tracks
   * Get tags and images for a track from a music stream service and save it them to your local track file
   * Create remote playlists from your local playlists

.. note::
   This guide will use Spotify, but any supported music streaming service can be used in generally the same way.
   Just modify the imports and classes as required.


.. include:: _howto/setup.logging.txt


Sync data
---------

1. Define a helper function to search for tracks and check the results:

   .. literalinclude:: _howto/scripts/sync/p1.py
      :language: Python
      :lines: 3-

2. Define a helper function to load the matched tracks, get tags from the music streaming service,
   and save the tags to the file:

   .. note::
      By default, URIs are saved to the ``comments`` tag.

   .. literalinclude:: _howto/scripts/sync/p2.py
      :language: Python
      :lines: 3-

3. Define a helper function to sync the local playlist with a remote playlist
   once all tracks in a playlist have URIs assigned:

   .. literalinclude:: _howto/scripts/sync/p3.py
      :language: Python
      :lines: 3-

4. Set up and load a remote API object and local library with a wrangler attached:

   .. literalinclude:: _howto/scripts/spotify.api.py
      :language: Python

   .. literalinclude:: _howto/scripts/sync/p4.py
      :language: Python
      :lines: 3-

4. Set up the remote library and run the program:

   .. literalinclude:: _howto/scripts/sync/p99.py
      :language: Python
      :lines: 3-
