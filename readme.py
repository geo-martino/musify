from syncify.shared.exception import SafeDict
from syncify.local.track import TRACK_FILETYPES, LocalTrack
from syncify.local.playlist import PLAYLIST_FILETYPES
from syncify.local.library import LIBRARY_CLASSES, LocalLibrary

from syncify.spotify import SPOTIFY_NAME

SRC_FILENAME = "README.template.md"
TRG_FILENAME = SRC_FILENAME.replace(".template", "")


def format_readme():
    """Format the readme template and save the formatted readme"""
    format_map = {
        "uri_tag": [LocalTrack.uri_tag.name.lower()],
        "local_sources": [cls.name for cls in LIBRARY_CLASSES if cls != LocalLibrary],
        "remote_sources": [SPOTIFY_NAME],
        "track_filetypes": TRACK_FILETYPES,
        "playlist_filetypes": PLAYLIST_FILETYPES,
    }
    format_map = SafeDict({k: "`" + "` `".join(v) + "`" for k, v in format_map.items()})

    with open(SRC_FILENAME, 'r') as file:
        template = file.read()

    formatted = template.format_map(format_map)
    with open(TRG_FILENAME, 'w') as file:
        file.write(formatted)


if __name__ == "__main__":
    format_readme()
