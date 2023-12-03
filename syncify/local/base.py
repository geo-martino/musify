from dataclasses import dataclass


class LocalObject:
    """Generic base class for locally-stored objects"""
    pass


@dataclass(frozen=True)
class TagMap:
    """Map of human-friendly tag name to ID3 tag ids for a given file type"""

    title: list[str]
    artist: list[str]
    album: list[str]
    album_artist: list[str]
    track_number: list[str]
    track_total: list[str]
    genres: list[str]
    year: list[str]
    bpm: list[str]
    key: list[str]
    disc_number: list[str]
    disc_total: list[str]
    compilation: list[str]
    comments: list[str]
    images: list[str]

    def __getitem__(self, key: str) -> list[str]:
        """Safely get the value of a given attribute key, returning an empty string if the key is not found"""
        return getattr(self, key, [])
