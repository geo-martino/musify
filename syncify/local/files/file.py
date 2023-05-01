from os.path import splitext
from typing import Optional

from syncify.local.files.tags.exception import IllegalFileTypeError
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
        raise IllegalFileTypeError(ext, f"Not an accepted extension. Use only: {', '.join(all_filetypes)}")


if __name__ == "__main__":
    from syncify.utils.logger import Logger

    Logger.set_dev()
    music_folder = "tests/__resources"

    flac = load_track(f"{music_folder}/noise_flac.flac")
    print(flac)

    mp3 = load_track(f"{music_folder}/noise_mp3.mp3")
    # print({k: v for k, v in mp3.file.items() if not k.startswith('APIC')})
    print(mp3)

    m4a = load_track(f"{music_folder}/noise_m4a.m4a")
    print(m4a)

    wma = load_track(f"{music_folder}/noise_wma.wma")
    print(wma)

    exit()

    music_folder = "/mnt/d/Music"

    FLAC.set_file_paths(music_folder)
    for path in FLAC.filepaths:
        file = load_track(path)
        if not file.valid:
            print(repr(file))

    MP3.set_file_paths(music_folder)
    for path in MP3.filepaths:
        file = load_track(path)
        if not file.valid:
            print(repr(file))

    M4A.set_file_paths(music_folder)
    for path in M4A.filepaths:
        file = load_track(path)
        if not file.valid:
            print(repr(file))

    WMA.set_file_paths(music_folder)
    for path in WMA.filepaths:
        file = load_track(path)
        if not file.valid:
            print(repr(file))
