from musify.local.library import LocalLibrary
library = LocalLibrary()

import json

path = "local_backup.json"
with open(path, "w") as file:
    json.dump(library.json(), file, indent=2)

with open(path, "r") as file:
    backup = json.load(file)
tracks = {track["path"]: track for track in backup["tracks"]}

library.restore_tracks(tracks)

from musify.local.track.field import LocalTrackField

tags = [
    LocalTrackField.TITLE,
    LocalTrackField.GENRES,
    LocalTrackField.KEY,
    LocalTrackField.BPM,
    LocalTrackField.DATE,
    LocalTrackField.COMPILATION,
    LocalTrackField.IMAGES
]

library.restore_tracks(tracks, tags=tags)

results = library.save_tracks(tags=tags, replace=True, dry_run=False)
library.log_sync_result(results)
