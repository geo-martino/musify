import importlib
import inspect
from os import listdir, sep
from os.path import join, dirname, splitext
from typing import Optional, MutableMapping, Mapping, List, Type

from local.files._track import Track
from local.files.tags.helpers import TagEnums
from utils.logger import Logger


def _get_filetype_class_map() -> Mapping[str, Track.__class__]:
    scripts = [".".join([*dirname(dirname(__file__)).split(sep), "files", splitext(f)[0]])
               for f in listdir(join(dirname(dirname(__file__)), "files"))
               if f.endswith("py") and not f.startswith("_")
               ]

    filetype_class_map: MutableMapping[str, Track.__class__] = {}
    for script in scripts:
        module = importlib.import_module(script)
        filetype_class_map.update({
            filetype: class_
            for class_, obj in inspect.getmembers(module, inspect.isclass) if obj.__module__.startswith(script)
            for filetype in obj.filetypes
        })

    return filetype_class_map


class File(Logger):

    filetype_class = _get_filetype_class_map()

    def __init__(self, path: str, position: Optional[int] = None):
        Logger.__init__(self)

        ext = splitext(path)[1]
        if ext not in self.filetype_class:
            self._logger.warning(
                f"{ext} not an accepted extension. "
                f"Use only: {', '.join(list(self.filetype_class.keys()))}"
            )

        self.track: Track = self.filetype_class[ext](path=path, position=position)

    @property
    def valid(self):
        if hasattr(self, 'track'):
            return self.track.valid
        else:
            return False

    def update_file_tags(self, tags: List[Type[TagEnums]] = None, replace: bool = False, dry_run: bool = True) -> None:
        """
        Update file's tags from given dictionary of tags.

        :param tags: Tags to be updated.
        :param replace: Destructively replace tags in each file.
        :param dry_run: Run function, but do not modify file at all.
        """
        self.track.load_file()
        track_disk = self.track.load_new()

        if tags is None:
            tags = list(TagEnums)

        if TagEnums.TITLE in tags and self.track.title != track_disk.title:
            self.track.update_title()
        if TagEnums.ARTIST in tags and self.track.artist != track_disk.artist:
            self.track.update_artist()
        if TagEnums.ALBUM in tags and self.track.album != track_disk.album:
            self.track.update_album()
        if TagEnums.ALBUM_ARTIST in tags and self.track.album_artist != track_disk.album_artist:
            self.track.update_album_artist()
        if TagEnums.TRACK in tags and (self.track.track_number != track_disk.track_number or self.track.track_total != track_disk.track_total):
            self.track.update_track()
        if TagEnums.GENRES in tags and self.track.genres != track_disk.genres:  # needs proper list comparison
            self.track.update_genres()
        if TagEnums.YEAR in tags and self.track.year != track_disk.year:
            self.track.update_year()
        if TagEnums.BPM in tags and self.track.bpm != track_disk.bpm:
            self.track.update_bpm()
        if TagEnums.KEY in tags and self.track.key != track_disk.key:
            self.track.update_key()
        if TagEnums.DISC in tags and (self.track.disc_number != track_disk.disc_number or self.track.disc_total != track_disk.disc_total):
            self.track.update_disc()
        if TagEnums.COMPILATION in tags and self.track.compilation != track_disk.compilation:
            self.track.update_compilation()
        if TagEnums.IMAGE in tags and self.track.has_image != track_disk.has_image:  # needs deeper comparison
            self.track.update_images()
        if TagEnums.COMMENTS in tags and self.track.comments != track_disk.comments:  # needs proper list comparison
            self.track.update_comments()
        if TagEnums.URI in tags and self.track.uri != track_disk.uri:  # needs deeper comparison
            self.track.update_uri()
