from pathlib import Path

from tests.utils import path_resources

path_api_resources = path_resources.joinpath(Path(__file__).parent.name)
path_token = path_api_resources.joinpath("token").with_suffix(".json")
