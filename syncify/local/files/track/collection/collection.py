from abc import ABCMeta, abstractmethod
from typing import List, Optional

from syncify.local.files.track import Track


class TrackCollection(metaclass=ABCMeta):

    @property
    @abstractmethod
    def tracks(self) -> Optional[List[Track]]:
        raise NotImplementedError

    def __len__(self):
        return len(self.tracks)
