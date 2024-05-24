from musify.libraries.local.track import FLAC, MP3, M4A, WMA

track = FLAC("<PATH TO A FLAC TRACK>")
track = MP3("<PATH TO AN MP3 TRACK>")
track = M4A("<PATH TO AN M4A TRACK>")
track = WMA("<PATH TO A WMA TRACK>")

# pretty print information about this track
print(track)
