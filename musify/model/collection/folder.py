from pydantic import Field, computed_field

from musify._types import StrippedString
from musify.model.item.track import Track, HasTracks
from musify.model.properties import HasName, HasLength


class Folder[KT, VT: Track](HasTracks[KT, VT], HasName, HasLength):
    """Represents a folder collection and its properties."""
    name: StrippedString = Field(
        description="The name of this folder.",
        alias="folder",
    )

    @computed_field(description="Folder is considered a compilation if over 50% of tracks are marked as compilation.")
    @property
    def compilation(self) -> bool:
        return (sum(track.album.compilation is True for track in self.tracks) / len(self.tracks)) > 0.5
