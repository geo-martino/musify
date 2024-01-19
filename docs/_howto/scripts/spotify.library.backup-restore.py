from musify.spotify.api import SpotifyAPI
from musify.spotify.library import SpotifyLibrary
api = SpotifyAPI()
library = SpotifyLibrary(api=api)

import json

path = "remote_backup.json"
with open(path, "w") as file:
    json.dump(library.json(), file, indent=2)

with open(path, "r") as file:
    backup = json.load(file)

library.restore_playlists(backup["playlists"])
results = library.sync(kind="refresh", reload=False, dry_run=False)
library.log_sync(results)
