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

1. Set up and load at least one local library with a remote wrangler attached, and one remote API object:

   .. literalinclude:: _howto/scripts/sync.py
      :language: Python
      :lines: 5-14

   .. literalinclude:: _howto/scripts/spotify.api.py
      :language: Python
      :lines: 1-20

2. Search for tracks and check the results:

   .. literalinclude:: _howto/scripts/sync.py
      :language: Python
      :lines: 16-27

3. Load the matched tracks, get tags from the music streaming service, and save the tags to the file:

   .. note::
      By default, URIs are saved to the ``comments`` tag.

   .. literalinclude:: _howto/scripts/sync.py
      :language: Python
      :lines: 29-48

4. Once all tracks in a playlist have URIs assigned, sync the local playlist with a remote playlist:

   .. literalinclude:: _howto/scripts/sync.py
      :language: Python
      :lines: 50-60
