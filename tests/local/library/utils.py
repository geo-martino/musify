from os.path import basename, join, dirname

from tests.utils import path_resources

path_library_resources = join(path_resources, basename(dirname(__file__)))
