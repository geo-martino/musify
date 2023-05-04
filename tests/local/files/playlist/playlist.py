from typing import Type, Optional, List

from syncify.local.files import Track
from tests.local.files.track.track import random_track


def random_tracks(number: int, cls: Optional[Type[Track]] = None) -> List[Track]:
    return [random_track(cls=cls) for _ in range(number)]


if __name__ == "__main__":
    [print(track) for track in random_tracks(20)]
