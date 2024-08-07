import datetime
import string
from pathlib import Path
from random import choice, randrange, sample
from typing import Any
from uuid import uuid4

from musify.types import MusifyEnum

path_tests = Path(__file__).parent
path_root = path_tests.parent
path_resources = path_tests.joinpath("__resources")

path_txt = path_resources.joinpath("test").with_suffix(".txt")

path_api_resources = path_resources.joinpath("api")
path_token = path_api_resources.joinpath("token").with_suffix(".json")


# noinspection SpellCheckingInspection
def idfn(value: Any) -> str | None:
    """Generate test ID for Spotify API tests"""
    if isinstance(value, MusifyEnum):
        return value.name
    return value


def random_str(start: int = 30, stop: int = 50) -> str:
    """Generates a random string of upper and lower case characters with a random length between the values given."""
    range_ = randrange(start=start, stop=stop) if start < stop else start
    return "".join(choice(string.ascii_letters) for _ in range(range_))


def random_file(tmp_path: Path, size: int | None = None) -> Path:
    """Generates a random file of a given ``size`` in bytes in the test cache folder and returns its path."""
    path = tmp_path.joinpath(str(uuid4())).with_suffix(".txt")
    with open(path, "w") as f:
        for _ in range(0, size or randrange(int(6*10e3), int(10e6))):
            f.write(choice(string.ascii_letters))
    return path


def random_dt(start: datetime = datetime.date(1970, 1, 3), stop: datetime = datetime.datetime.now()) -> datetime:
    """Generates a random date string in the form YYYY-MM-DD."""
    if isinstance(start, datetime.date):
        start = datetime.datetime.combine(start, datetime.time(0, 0, 0))
    if isinstance(stop, datetime.date):
        stop = datetime.datetime.combine(stop, datetime.time(0, 0, 0))
    timestamp = randrange(start=int(start.timestamp()), stop=int(stop.timestamp()))
    return datetime.datetime.fromtimestamp(timestamp)


def random_date_str(start: datetime = datetime.date(1970, 1, 3), stop: datetime = datetime.datetime.now()) -> str:
    """Generates a random date string in the form YYYY-MM-DD."""
    if isinstance(start, datetime.date):
        start = datetime.datetime.combine(start, datetime.time(0, 0, 0))
    if isinstance(stop, datetime.date):
        stop = datetime.datetime.combine(stop, datetime.time(0, 0, 0))
    return random_dt(start=start, stop=stop).strftime("%Y-%m-%d")


# noinspection SpellCheckingInspection
GENRES: tuple[str, ...] = tuple(genre.lower() for genre in (
    "Adult Contemporary",
    "Arab Pop",
    "Baroque",
    "Britpop",
    "Bubblegum Pop",
    "Chamber Pop",
    "Chanson",
    "Christian Pop",
    "Classical Crossover",
    "Europop",
    "Dance Pop",
    "Dream Pop",
    "Electro Pop",
    "Iranian Pop",
    "Jangle Pop",
    "Latin Ballad",
    "Levenslied",
    "Louisiana Swamp Pop",
    "Mexican Pop",
    "Motorpop",
    "New Romanticism",
    "Orchestral Pop",
    "Pop Rap",
    "Popera",
    "Pop/Rock",
    "Pop Punk",
    "Power Pop",
    "Psychedelic Pop",
    "Schlager",
    "Soft Rock",
    "Sophisti-Pop",
    "Space Age Pop",
    "Sunshine Pop",
    "Surf Pop",
    "Synthpop",
    "Teen Pop",
    "Traditional Pop Music",
    "Turkish Pop",
    "Vispop",
    "Wonky Pop"
))


def random_genres(size: int | None = None) -> list[str]:
    """Return a list of random genres."""
    return sample(GENRES, min(size, len(GENRES)) if size else randrange(0, len(GENRES)))
