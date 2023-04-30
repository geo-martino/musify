import importlib
import inspect
import sys
from os import listdir
from os.path import splitext, dirname, basename
from types import ModuleType
from typing import Optional, List

from _track import Track
from flac import FLAC
from m4a import M4A
from mp3 import MP3
from wma import WMA


def load_track(path: str, position: Optional[int] = None):
    ext = splitext(path)[1].lower()

    if ext in FLAC.filetypes:
        return FLAC(file=path, position=position)
    elif ext in MP3.filetypes:
        return MP3(file=path, position=position)
    elif ext in M4A.filetypes:
        return M4A(file=path, position=position)
    elif ext in WMA.filetypes:
        return WMA(file=path, position=position)
    else:
        raise NotImplementedError(
            f"{ext} not an accepted extension. "
            f"Use only: {', '.join(filetypes)}"
        )


filetype_scripts: List[str] = [
    splitext(f)[0]
    for f in listdir(dirname(__file__))
    if f.endswith("py") and f != basename(Track.__name__) and not f.startswith("_")
]

filetype_modules: List[ModuleType] = [
    importlib.import_module(script) if script not in sys.modules else importlib.reload(sys.modules[script])
    for script in filetype_scripts
]

filetypes: List[str] = [
    filetype
    for module in filetype_modules
    for class_, obj in inspect.getmembers(module, inspect.isclass)
    if issubclass(obj.__class__, Track.__class__) and class_ != Track.__name__
    for filetype in obj.filetypes
]

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
