from musify.local.library import LocalLibrary

library = LocalLibrary(
    library_folders=["<PATH TO YOUR LIBRARY FOLDER>", ...],
    playlist_folder="<PATH TO YOUR PLAYLIST FOLDER",
)

from musify.local.library import MusicBee

library = MusicBee(musicbee_folder="<PATH TO YOUR MUSICBEE FOLDER>")

# if you have a very large library, this will take some time...
library.load()

# ...or you may also just load distinct sections of your library
library.load_tracks()
library.load_playlists()

# optionally log stats about these sections
library.log_tracks()
library.log_playlists()

# pretty print an overview of your library
print(library)

playlist = library.playlists["<NAME OF YOUR PLAYLIST>"]  # case sensitive
album = next(album for album in library.albums if album.name == "<ALBUM NAME>")
artist = next(artist for artist in library.artists if artist.name == "<ARTIST NAME>")
folder = next(folder for folder in library.folders if folder.name == "<ALBUM NAME>")
genre = next(genre for genre in library.genres if genre.name == "<GENRE NAME>")

# pretty print information about the loaded objects
print(playlist, album, artist, folder, genre, sep="\n")

# get a track via its title
track = library["<TRACK TITLE>"]  # if multiple tracks have the same title, the first matching one if returned

# get a track via its path
track = library["<PATH TO YOUR TRACK>"]  # must be an absolute path

# get a track according to a specific tag
track = next(track for track in library if track.artist == "<ARTIST NAME>")
track = next(track for track in library if "<GENRE>" in track.genres)

# pretty print information about this track
print(track)
