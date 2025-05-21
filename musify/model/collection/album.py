from pydantic import computed_field, PositiveInt

from musify.model.item.album import _Album
from musify.model.item.artist import Artist
from musify.model.item.genre import Genre
from musify.model.item.track import HasTracks, Track


class AlbumCollection[TK, TV: Track, RT: Artist, GT: Genre](_Album[RT, GT], HasTracks[TK, TV]):

    @computed_field
    @property
    def track_total(self) -> PositiveInt:
        return len(self.tracks)

    @computed_field
    @property
    def disc_total(self) -> PositiveInt | None:
        values = set(
            track.disc.total
            for track in self.tracks
            if track.disc is not None and track.disc.total is not None
        )
        return max(values) if values else None
