import datetime
import re
import string
from os.path import join, dirname
from random import choice, randrange, sample
from uuid import uuid4

import pytest

path_root = dirname(dirname(__file__))
path_tests = dirname(__file__)
path_resources = join(dirname(__file__), "__resources")

path_txt = join(path_resources, "test.txt")


def get_stdout(capfd: pytest.CaptureFixture) -> str:
    """Utility function which returns stdout from ``capfd`` with ANSI colour codes removed"""
    return re.sub("\33.*?m", "", capfd.readouterr().out)


def random_str(start: int = 30, stop: int = 50) -> str:
    """Generates a random string of upper and lower case characters with a random length between the values given."""
    range_ = randrange(start=start, stop=stop) if start < stop else start
    return "".join(choice(string.ascii_letters) for _ in range(range_))


def random_file(tmp_path: str, size: int | None = None) -> str:
    """Generates a random file of a given ``size`` in bytes in the test cache folder and returns its path."""
    path = join(tmp_path, str(uuid4()) + ".txt")
    with open(path, 'w') as f:
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
