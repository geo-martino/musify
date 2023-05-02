from abc import ABC, abstractmethod
from typing import List, MutableMapping

from syncify.local.files.track.track import Track


class TrackCollection(ABC):

    @property
    @abstractmethod
    def tracks(self) -> List[Track]:
        raise NotImplementedError

    @abstractmethod
    def as_dict(self) -> MutableMapping[str, object]:
        """Return a dictionary representation of this collection without tracks"""
        raise NotImplementedError

    @abstractmethod
    def as_json(self) -> MutableMapping[str, object]:
        """Return a dictionary representation of this collection  without tracks that is safe to output to json"""
        raise NotImplementedError

    def __str__(self) -> str:
        result = f"{self.__class__.__name__}(\n{{}}\n)"
        attributes = self.as_dict()
        attributes["tracks"] = self.tracks
        indent = 2

        max_width = max(len(tag_name) for tag_name in attributes)
        attributes_repr = []
        for key, attribute in attributes.items():
            if isinstance(attribute, list) and len(attribute) > 0 and isinstance(attribute[0], Track):
                tracks_repr = f"[\n{{}}\n" + " " * indent + "]"
                tracks = [" " * indent * 2 + str(track).replace("\n", "\n" + " " * indent * 2) for track in attribute]
                attribute = tracks_repr.format(",\n".join(tracks))
                attributes_repr.append(f"{key.title() : <{max_width}} = {attribute}")
            else:
                attributes_repr.append(f"{key.title() : <{max_width}} = {repr(attribute)}")

        return result.format("\n".join([" " * indent + attribute for attribute in attributes_repr]))

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.as_dict()})"
