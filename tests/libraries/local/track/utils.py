import string
from datetime import datetime
from os.path import join
from random import choice, randrange, randint

import mutagen
from dateutil.relativedelta import relativedelta

from musify.libraries.local.track import TRACK_CLASSES, LocalTrack
from tests.libraries.local.utils import remote_wrangler, path_track_resources
from tests.libraries.remote.spotify.utils import random_uri
from tests.utils import random_str, random_dt, random_genres


class MutagenMock(mutagen.FileType):
    class MutagenInfoMock(mutagen.StreamInfo):
        def __init__(self):
            self.length = randrange(int(10e4), int(6*10e5))  # 1 second to 10 minutes range
            self.channels = randrange(1, 5)
            self.bitrate = randrange(96, 1400) * 1000
            self.sample_rate = choice([44.1, 48, 88.2, 96]) * 1000

    # noinspection PyMissingConstructor
    def __init__(self):
        self.info = self.MutagenInfoMock()
        self.pictures = []


# noinspection PyProtectedMember
def random_track[T: LocalTrack](cls: type[T] | None = None) -> T:
    """Generates a new, random track of the given class."""
    if cls is None:
        cls = choice(tuple(TRACK_CLASSES))
    track = cls.__new__(cls)
    super(LocalTrack, track).__init__()

    track._available_paths = set()
    track._available_paths_lower = set()

    file = MutagenMock()
    file.info.length = randint(30, 600)

    track._reader = track._create_reader(file=file, tag_map=track.tag_map, remote_wrangler=remote_wrangler)
    track._writer = track._create_writer(file=file, tag_map=track.tag_map, remote_wrangler=remote_wrangler)
    track.remote_wrangler = remote_wrangler

    track._loaded = True

    track.title = random_str(30, 50)
    track.artist = random_str(30, 50)
    track.album = random_str(30, 50)
    track.album_artist = random_str(30, 50)
    track.track_number = randrange(1, 20)
    track.track_total = randint(track.track_number, 20)
    track.genres = random_genres()
    track.date = random_dt()
    track.bpm = randint(6000, 15000) / 100
    track.key = choice(string.ascii_uppercase[:7])
    track.disc_number = randrange(1, 8)
    track.disc_total = randint(track.disc_number, 20)
    track.compilation = choice([True, False])
    track.comments = [random_str(20, 50) for _ in range(randrange(3))]

    has_uri = choice([True, False])
    track.uri = random_uri() if has_uri else remote_wrangler.unavailable_uri_dummy

    track.image_links = {}
    track.has_image = False

    filename_ext = f"{str(track.track_number).zfill(2)} - {track.title}" + choice(tuple(track.valid_extensions))
    track._reader.file.filename = join(path_track_resources, random_str(30, 50), filename_ext)

    track.date_added = datetime.now() - relativedelta(days=randrange(8, 20), hours=randrange(1, 24))
    track.last_played = datetime.now() - relativedelta(days=randrange(1, 6), hours=randrange(1, 24))
    track.play_count = randrange(200)
    track.rating = randrange(0, 100)

    return track


def random_tracks[T: LocalTrack](number: int | None = None, cls: type[T] | None = None) -> list[T]:
    """Generates a ``number`` of random tracks of the given class."""
    return [random_track(cls=cls) for _ in range(number or randrange(2, 20))]
