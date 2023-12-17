import string
from datetime import datetime
from os.path import join, basename, dirname
from random import choice, randrange, randint

import mutagen
from dateutil.relativedelta import relativedelta

from syncify.local.track import TRACK_CLASSES, LocalTrack
# noinspection PyProtectedMember
from syncify.local.track._base.writer import TagWriter
from tests.local.utils import remote_wrangler
from tests.spotify.utils import random_uri
from tests.utils import path_resources, random_str

path_track_resources = join(path_resources, basename(dirname(__file__)))
path_track_flac = join(path_track_resources, "noise_flac.flac")
path_track_mp3 = join(path_track_resources, "noise_mp3.mp3")
path_track_m4a = join(path_track_resources, "noise_m4a.m4a")
path_track_wma = join(path_track_resources, "noise_wma.wma")
path_track_img = join(path_track_resources, "track_image.jpg")
path_track_all: set[str] = {path for c in TRACK_CLASSES for path in c.get_filepaths(path_track_resources)}


class MutagenMock(mutagen.FileType):
    class MutagenInfoMock(mutagen.StreamInfo):
        def __init__(self):
            self.length = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mock = True
        self.info = self.MutagenInfoMock()
        self.pictures = []


def random_track[T: LocalTrack](cls: type[T] | None = None) -> T:
    """Generates a new, random track of the given class."""
    if cls is None:
        cls = choice(tuple(TRACK_CLASSES))
    track = cls.__new__(cls)
    TagWriter.__init__(track, remote_wrangler=remote_wrangler)
    track._available_paths = set()
    track._available_paths_lower = set()

    track._file = MutagenMock()
    track.file.info.length = randint(30, 600)

    track.title = random_str(20, 50)
    track.artist = random_str(20, 50)
    track.album = random_str(20, 50)
    track.album_artist = random_str(20, 50)
    track.track_number = randrange(1, 20)
    track.track_total = randint(track.track_number, 20)
    track.genres = [random_str(20, 50) for _ in range(randrange(7))]
    track.year = randrange(1950, datetime.now().year + 1)
    track.bpm = randint(6000, 15000) / 100
    track.key = choice(string.ascii_uppercase[:7])
    track.disc_number = randrange(1, 8)
    track.disc_total = randint(track.disc_number, 20)
    track.compilation = choice([True, False])
    track.comments = [random_str(20, 50) for _ in range(randrange(3))]

    has_uri = choice([True, False])
    track.uri = random_uri() if has_uri else remote_wrangler.unavailable_uri_dummy

    track._image_links = {}
    track.has_image = False

    ext = choice(tuple(track.valid_extensions))
    path = join(path_track_resources, random_str(20, 50), f"{str(track.track_number).zfill(2)} - {track.title}" + ext)
    track._path = path
    track.file.filename = path

    track.date_added = datetime.now() - relativedelta(days=randrange(8, 20), hours=randrange(1, 24))
    track.last_played = datetime.now() - relativedelta(days=randrange(1, 6), hours=randrange(1, 24))
    track.play_count = randrange(200)
    track.rating = randrange(0, 100, 20)

    return track


def random_tracks[T: LocalTrack](number: int = randrange(2, 20), cls: type[T] | None = None) -> list[T]:
    """Generates a ``number`` of random tracks of the given class."""
    return [random_track(cls=cls) for _ in range(number)]
