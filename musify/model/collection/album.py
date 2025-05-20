from musify.model.item.album import Album
from musify.model.item.track import HasTracks, Track


class AlbumCollection[KT, VT: Track](Album, HasTracks[KT, VT]):
    pass
