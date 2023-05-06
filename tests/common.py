import os
import string
from os.path import join, dirname, exists
from random import choice, randrange

path_root = dirname(dirname(__file__))

path_cache = join(path_root, ".test_cache")
if not exists(path_cache):
    os.makedirs(path_cache)

path_resources = join(dirname(__file__), "__resources")

path_txt = join(path_resources, "test.txt")


def random_str(start: int = 1, stop: int = 20) -> str:
    return ''.join(choice(string.ascii_letters) for _ in range(randrange(start, stop)))

