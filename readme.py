from musify import PROGRAM_OWNER_USER, PROGRAM_NAME
from musify.local.track import TRACK_FILETYPES, LocalTrack
from musify.local.playlist import PLAYLIST_FILETYPES
from musify.local.library import LIBRARY_CLASSES, LocalLibrary
from musify.shared.exception import SafeDict
from musify.spotify import SPOTIFY_NAME

SRC_FILENAME = "README.template.md"
TRG_FILENAME = SRC_FILENAME.replace(".template", "")


def format_readme():
    """Format the readme template and save the formatted readme"""
    format_map_standard = {
        "program_name": PROGRAM_NAME,
        "program_name_lower": PROGRAM_NAME.lower(),
        "program_owner_user": PROGRAM_OWNER_USER,
    }
    format_map_code = {
        "uri_tag": [LocalTrack.uri_tag.name.lower()],
        "local_sources": [cls.name for cls in LIBRARY_CLASSES if cls != LocalLibrary],
        "remote_sources": [SPOTIFY_NAME],
        "track_filetypes": TRACK_FILETYPES,
        "playlist_filetypes": PLAYLIST_FILETYPES,
    }
    format_map_code = {k: "`" + "` `".join(v) + "`" for k, v in format_map_code.items()}
    format_map = SafeDict(format_map_standard | format_map_code)

    with open(SRC_FILENAME, 'r') as file:
        template = file.read()

    formatted = template.format_map(format_map)
    with open(TRG_FILENAME, 'w') as file:
        file.write(formatted)


if __name__ == "__main__":
    format_readme()
    print(f"Formatted {TRG_FILENAME} file using template: {SRC_FILENAME}")
