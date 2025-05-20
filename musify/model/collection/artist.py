from musify.model.item.album import HasAlbums, Album
from musify.model.item.artist import Artist
from musify.model.item.genre import Genre
from musify.model.item.track import HasTracks, Track


class ArtistCollection[TK, TV: Track, AT: Album, GT: Genre](Artist[GT], HasTracks[TK, TV], HasAlbums[AT]):
    """Represents a collection of artists and their properties."""
    pass
