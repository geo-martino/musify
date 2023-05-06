from abc import ABCMeta, abstractmethod
from typing import List

from syncify.local.files.track import LocalTrack


class TrackCollection(metaclass=ABCMeta):

    @property
    @abstractmethod
    def tracks(self) -> List[LocalTrack]:
        raise NotImplementedError

    def __len__(self):
        return len(self.tracks)
