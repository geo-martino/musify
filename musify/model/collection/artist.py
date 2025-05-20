from musify.model.item.album import HasAlbums, Album
from musify.model.item.artist import Artist
from musify.model.item.track import HasTracks, Track


class ArtistCollection[KT, VT: Track, AT: Album](Artist, HasTracks[KT, VT], HasAlbums[AT]):
    """Represents a collection of artists and their properties."""
    pass
