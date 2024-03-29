from musify.libraries.local.library import LocalLibrary
local_library = LocalLibrary()

from musify.libraries.remote.spotify.api import SpotifyAPI
from musify.libraries.remote.spotify.library import SpotifyLibrary
api = SpotifyAPI()
remote_library = SpotifyLibrary(api=api)

from musify.report import report_playlist_differences

report_playlist_differences(source=local_library, reference=remote_library)

from musify.libraries.local.track.field import LocalTrackField
from musify.report import report_missing_tags

tags = [
    LocalTrackField.TITLE,
    LocalTrackField.GENRES,
    LocalTrackField.KEY,
    LocalTrackField.BPM,
    LocalTrackField.DATE,
    LocalTrackField.COMPILATION,
    LocalTrackField.IMAGES
]

report_missing_tags(collections=local_library, tags=tags, match_all=False)
