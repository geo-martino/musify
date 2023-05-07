from abc import ABCMeta, abstractmethod
from typing import List

from syncify.local.files.track import LocalTrack
from syncify.utils_new.generic import PrettyPrinter


class TrackCollection(PrettyPrinter, metaclass=ABCMeta):

    @property
    @abstractmethod
    def tracks(self) -> List[LocalTrack]:
        raise NotImplementedError

    def __len__(self):
        return len(self.tracks)

    def __iter__(self):
        return (t for t in self.tracks)
