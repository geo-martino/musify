import requests
import datetime

from musify import PROGRAM_NAME


def get_version() -> str:
    """Calculate the new version of the package based on the currently released latest version"""
    url = f"https://pypi.python.org/pypi/{PROGRAM_NAME.lower()}/json"
    data = requests.get(url).json()
    major, minor, patch = tuple(map(int, data["info"]["version"].split(".")))

    dt = datetime.datetime.now(datetime.UTC)
    if major != dt.year or minor != dt.month:
        patch = -1

    return ".".join(map(str, [dt.year, dt.month, patch + 1]))


__version__ = get_version()
