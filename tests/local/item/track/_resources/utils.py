import mimetypes
from pathlib import Path

TRACK_RESOURCE_PATH = Path(__file__).parent.joinpath("_resources")
TRACK_PATHS = [
    path for path in TRACK_RESOURCE_PATH.rglob("*")
    if mimetypes.guess_type(path)[0].startswith("audio")
]

