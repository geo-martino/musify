import urllib.parse
from datetime import datetime
from os.path import join, exists, normpath
from typing import Optional, Set, Any, List, MutableMapping

from lxml import etree

from syncify.local.files.track.base import LocalTrack
from syncify.local.library.library import Library


class MusicBee(Library):

    def __init__(
            self,
            library_folder: Optional[str] = None,
            musicbee_folder: str = "MusicBee",
            other_folders: Optional[Set[str]] = None,
            load: bool = True
    ):
        if not exists(musicbee_folder):
            musicbee_in_library = join(library_folder, musicbee_folder)
            if not exists(musicbee_in_library):
                raise FileNotFoundError(f"Cannot find MusicBee library at given path: "
                                        f"{musicbee_folder} OR {musicbee_in_library}")
            musicbee_folder = musicbee_in_library

        self.xml: MutableMapping[str, Any] = {}
        for record in ReadXmlLibrary(join(musicbee_folder, "iTunes Music Library.xml")):
            for key, value in record.items():
                self.xml[key] = value

        Library.__init__(
            self,
            playlist_folder=join(musicbee_folder, "Playlists"),
            library_folder=library_folder,
            other_folders=other_folders,
            load=load
        )

    @staticmethod
    def _xml_ts_to_dt(timestamp_str: Optional[str]) -> Optional[datetime]:
        if timestamp_str:
            return datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S%z")

    @staticmethod
    def _clean_xml_filepath(path: str) -> str:
        return normpath(urllib.parse.unquote(path.replace("file://localhost/", "")))

    def load_tracks(self) -> List[LocalTrack]:
        tracks_paths = {track.path.lower(): track for track in self._load_tracks()}
        tracks_xml = self.xml['Tracks'].values()

        for track_xml in self._get_progress_bar(iterable=tracks_xml, desc="Enriching metadata", unit="tracks"):
            if not track_xml['Location'].startswith('file://localhost/'):
                continue

            track = tracks_paths.get(self._clean_xml_filepath(track_xml['Location']).lower())
            if track is None:
                continue

            track.date_added = self._xml_ts_to_dt(track_xml.get('Date Added'))
            track.last_played = self._xml_ts_to_dt(track_xml.get('Play Date UTC'))
            track.play_count = int(track_xml.get('Play Count', 0))
            track.rating = int(track_xml.get('Rating')) if track_xml.get('Rating') is not None else None

        return list(tracks_paths.values())


class ReadXmlLibrary:
    def __init__(self, fh):
        """
        Initialize 'iterparse' to generate 'start' and 'end' events on all tags

        :param fh: File Handle from the XML File to parse
        """
        self.context = etree.iterparse(fh, events=("start", "end",))

    def _parse(self):
        """
        Yield only at 'end' event, except 'start' from tag 'dict'
        :return: yield current Element
        """
        for event, elem in self.context:
            if elem.tag == 'plist' or \
                    (event == 'start' and not elem.tag == 'dict'):
                continue
            yield elem

    def _parse_key_value(self, key=None):
        _dict = {}
        for elem in self._parse():
            if elem.tag == 'key':
                key = elem.text
                continue

            if elem.tag in ['integer', 'string', 'date']:
                if key is not None:
                    _dict[key] = elem.text
                    key = None
                else:
                    print('Missing key for value {}'.format(elem.text))

            elif elem.tag in ['true', 'false']:
                _dict[key] = elem.tag == 'true'

            elif elem.tag == 'dict':
                if key is not None:
                    _dict[key] = self._parse_dict(key)
                    key = None
                else:
                    return elem, _dict
            else:
                pass
                # print('Unknown tag {}'.format(elem.tag))

    # noinspection PyUnusedLocal
    def _parse_dict(self, key=None):
        elem = next(self._parse())
        elem, _dict = self._parse_key_value(elem.text)
        return _dict

    def __iter__(self):
        for elem in self._parse():
            if elem.tag == 'dict':
                try:
                    yield self._parse_dict()
                except StopIteration:
                    return
            else:
                pass
                # print('Unknown tag {}'.format(elem.tag))


if __name__ == "__main__":
    mb = MusicBee(library_folder="D:\\Music")
    print(mb)
