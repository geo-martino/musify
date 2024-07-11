from p1_load import *

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
