from os.path import basename, join, dirname

from syncify.local.library import LocalLibrary
from tests import path_resources

path_library_resources = join(path_resources, basename(dirname(__file__)))
