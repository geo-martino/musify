Sync data between local and remote libraries
============================================

In this example, you will:
   * Search for local tracks on a music streaming service and assign unique remote IDs to tags in your local tracks
   * Get tags and images for a track from a music stream service and save it them to your local track file
   * Create remote playlists from your local playlists

Note:
   This guide will use Spotify, but any supported music streaming service can be used in generally the same way.
   Just modify the imports and classes as required.

1. Set up and load at least one local library with a remote wrangler attached, and one remote API object:

   .. literalinclude:: _howto/scripts/sync.py
      :language: Python
      :lines: 1-25

2. Search for tracks and check the results:

   .. literalinclude:: _howto/scripts/sync.py
      :language: Python
      :lines: 27-35

3. Load the matched tracks, get tags from the music streaming service, and save the tags to the file:

   **NOTE**: By default, URIs are saved to the ``comments`` tag.

   .. literalinclude:: _howto/scripts/sync.py
      :language: Python
      :lines: 37-56

4. Once all tracks in a playlist have URIs assigned, sync the local playlist with a remote playlist:

   .. literalinclude:: _howto/scripts/sync.py
      :language: Python
      :lines: 58-69
