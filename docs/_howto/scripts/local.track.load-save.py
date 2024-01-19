from musify.local.track import FLAC, MP3, M4A, WMA

track = FLAC("<PATH TO A FLAC TRACK>")
track = MP3("<PATH TO AN MP3 TRACK>")
track = M4A("<PATH TO AN M4A TRACK>")
track = WMA("<PATH TO A WMA TRACK>")

# pretty print information about this track
print(track)

from musify.local.track import load_track

track = load_track("<PATH TO AN MP3 TRACK>")

from musify.spotify.processors.wrangle import SpotifyDataWrangler

track = MP3("<PATH TO AN MP3 TRACK>", remote_wrangler=SpotifyDataWrangler())

from datetime import date

track.title = "new title"
track.artist = "new artist"
track.album = "new album"
track.track_number = 200
track.genres = ["super cool genre", "awesome genre"]
track.key = "C#"
track.bpm = 120.5
track.date = date(year=2024, month=1, day=1)
track.compilation = True
track.image_links.update({
    "cover front": "https://i.scdn.co/image/ab67616d0000b2737f0918f1560fc4b40b967dd4",
    "cover back": "<PATH TO AN IMAGE ON YOUR LOCAL DRIVE>"
})

# see the updated information
print(track)

# save all the tags like so...
track.save(replace=True, dry_run=False)

# ...or select which tags you wish to save like so
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

track.save(tags=tags, replace=True, dry_run=False)
