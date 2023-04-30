from os.path import splitext
from typing import Optional

from syncify.local.files.flac import FLAC
from syncify.local.files.m4a import M4A
from syncify.local.files.mp3 import MP3
from syncify.local.files.wma import WMA


def load_track(path: str, position: Optional[int] = None):
    ext = splitext(path)[1].lower()
    track_classes = [FLAC, MP3, M4A, WMA]

    if ext in FLAC.filetypes:
        return FLAC(file=path, position=position)
    elif ext in MP3.filetypes:
        return MP3(file=path, position=position)
    elif ext in M4A.filetypes:
        return M4A(file=path, position=position)
    elif ext in WMA.filetypes:
        return WMA(file=path, position=position)
    else:
        all_filetypes = [filetype for c in track_classes for filetype in c.filetypes]
        raise NotImplementedError(
            f"{ext} not an accepted extension. "
            f"Use only: {', '.join(all_filetypes)}"
        )


if __name__ == "__main__":
    from syncify.utils.logger import Logger

    Logger.set_dev()
    music_folder = "tests/__resources"

    flac = load_track(f"{music_folder}/noise.flac")
    print(repr(flac))

    mp3 = load_track(f"{music_folder}/noise.mp3")
    print(repr(mp3))

    m4a = load_track(f"{music_folder}/noise.m4a")
    print(repr(m4a))

    wma = load_track(f"{music_folder}/noise.wma")
    print(repr(wma))

    music_folder = "/mnt/d/Music"

    FLAC.set_file_paths(music_folder)
    for path in FLAC._filepaths:
        file = load_track(path)
        if not file.valid:
            print(repr(file))

    MP3.set_file_paths(music_folder)
    for path in MP3._filepaths:
        file = load_track(path)
        if not file.valid:
            print(repr(file))

    M4A.set_file_paths(music_folder)
    for path in M4A._filepaths:
        file = load_track(path)
        if not file.valid:
            print(repr(file))

    WMA.set_file_paths(music_folder)
    for path in WMA._filepaths:
        file = load_track(path)
        if not file.valid:
            print(repr(file))
