from os.path import join, basename, dirname

from tests.utils import path_resources

path_api_resources = join(path_resources, basename(dirname(__file__)))
