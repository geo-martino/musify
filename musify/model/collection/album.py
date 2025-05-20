from musify.model.item.album import Album
from musify.model.item.artist import Artist
from musify.model.item.genre import Genre
from musify.model.item.track import HasTracks, Track


class AlbumCollection[TK, TV: Track, RT: Artist, GT: Genre](Album[RT, GT], HasTracks[TK, TV]):
    pass
