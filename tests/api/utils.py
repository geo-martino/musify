from os.path import join, basename, dirname

from tests.utils import path_resources

path_api_resources = join(path_resources, str(basename(dirname(__file__))))
path_token = join(path_api_resources, "token.json")
