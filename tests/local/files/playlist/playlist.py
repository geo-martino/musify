from typing import Type, Optional, List

from syncify.local.files.track import Track
from tests.local.files.track.track import random_track


if __name__ == "__main__":
    [print(track) for track in random_tracks(20)]

