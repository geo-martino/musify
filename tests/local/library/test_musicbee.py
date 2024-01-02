from datetime import datetime
from os.path import basename, splitext, join, dirname, relpath, getmtime

import pytest

from syncify.local.exception import MusicBeeError, FileDoesNotExistError
from syncify.local.library import LocalLibrary, MusicBee
# noinspection PyProtectedMember
from syncify.local.library._musicbee import XMLLibraryParser
from syncify.local.track import LocalTrack
from syncify.remote.processors.wrangle import RemoteDataWrangler
from tests.local.library.utils import LocalLibraryTester
from tests.local.library.utils import path_library_resources
from tests.local.playlist.utils import path_playlist_resources, path_playlist_m3u
from tests.local.playlist.utils import path_playlist_xautopf_bp, path_playlist_xautopf_ra
from tests.local.utils import random_track, path_track_all, path_track_mp3, path_track_flac, path_track_wma
from tests.utils import path_resources

library_filename = "musicbee_library.xml"
library_filepath = join(path_library_resources, library_filename)


class TestMusicBee(LocalLibraryTester):

    @pytest.fixture
    def library(self) -> LocalLibrary:
        MusicBee.xml_library_filename = library_filename
        library = MusicBee(
            library_folder=path_resources,
            musicbee_folder=path_library_resources,
            playlist_folder=path_playlist_resources,
        )
        library.load()

        # needed to ensure __setitem__ check passes
        library.items.append(random_track(cls=library[0].__class__))
        return library

    @pytest.fixture(scope="class")
    def blank_library(self) -> LocalLibrary:
        library = MusicBee(musicbee_folder=path_library_resources)
        assert library._path == library_filepath
        return library

    @pytest.mark.parametrize("path", [library_filepath], indirect=["path"])
    def test_parser(self, path: str):
        parser = XMLLibraryParser(path=path, path_keys=MusicBee.xml_path_keys)

        xml = parser.parse()
        assert xml["Major Version"] == 3
        assert xml["Minor Version"] == 5
        assert xml["Application Version"] == "3.5.8447.35892"
        assert xml["Music Folder"].endswith(relpath(dirname(path_library_resources)).lstrip("./\\"))
        assert xml["Library Persistent ID"] == "3D76B2A6FD362901"
        assert len(xml["Tracks"]) == 6
        assert len(xml["Playlists"]) == 3

        xml["Major Version"] = 7
        xml["Minor Version"] = 9
        xml["Music Folder"] = join("this", "is", "a", "new", "path")
        parser.unparse(xml, dry_run=False)

        xml_new = parser.parse()
        assert xml_new["Major Version"] == 7
        assert xml_new["Minor Version"] == 9
        assert xml_new["Application Version"] == xml["Application Version"]
        assert xml_new["Music Folder"] == xml["Music Folder"]
        assert xml_new["Library Persistent ID"] == xml["Library Persistent ID"]
        assert len(xml_new["Tracks"]) == len(xml["Tracks"])
        assert len(xml_new["Playlists"]) == len(xml["Playlists"])

    def test_init_fails(self):
        with pytest.raises(FileDoesNotExistError, match="MusicBee"):
            MusicBee()

        with pytest.raises(MusicBeeError):
            MusicBee(musicbee_folder=None)

        library_path_error = join(path_library_resources, "MusicBee")
        with pytest.raises(FileDoesNotExistError, match=f".*{library_path_error.replace('\\', '\\\\')}"):
            MusicBee(library_folder=path_library_resources)

        library_path_error = join(path_playlist_resources, MusicBee.xml_library_filename)
        with pytest.raises(FileDoesNotExistError, match=f".*{library_path_error.replace('\\', '\\\\')}"):
            MusicBee(musicbee_folder=path_playlist_resources)

    def test_init_no_playlists(self):
        library_no_playlists = MusicBee(
            library_folder=path_resources,
            musicbee_folder=basename(path_library_resources),
            playlist_folder="does_not_exist",
        )
        assert library_no_playlists.library_folder == path_resources
        assert library_no_playlists._path == library_filepath
        assert all(path in library_no_playlists._track_paths for path in path_track_all)
        assert library_no_playlists.playlist_folder is None

    def test_init_include(self):
        library_include = MusicBee(
            library_folder=path_resources,
            musicbee_folder=basename(path_library_resources),
            playlist_folder=basename(path_playlist_resources),
            include=[splitext(basename(path_playlist_m3u))[0], splitext(basename(path_playlist_xautopf_bp))[0]],
        )
        assert library_include.playlist_folder == path_playlist_resources
        assert library_include._playlist_paths == {
            splitext(basename(path_playlist_m3u).casefold())[0]: path_playlist_m3u,
            splitext(basename(path_playlist_xautopf_bp).casefold())[0]: path_playlist_xautopf_bp,
        }

    def test_init_exclude(self):
        library_exclude = MusicBee(
            library_folder=path_resources,
            musicbee_folder=basename(path_library_resources),
            playlist_folder=basename(path_playlist_resources),
            exclude=[splitext(basename(path_playlist_xautopf_bp))[0]],
        )
        assert library_exclude.playlist_folder == path_playlist_resources
        assert library_exclude._playlist_paths == {
            splitext(basename(path_playlist_m3u).casefold())[0]: path_playlist_m3u,
            splitext(basename(path_playlist_xautopf_ra).casefold())[0]: path_playlist_xautopf_ra,
        }

    def test_load(self):
        MusicBee.xml_library_filename = library_filename
        library = MusicBee(
            library_folder=path_resources,
            musicbee_folder=path_library_resources,
            playlist_folder=path_playlist_resources,
        )
        library.load()
        playlists = {name: pl.path for name, pl in library.playlists.items()}

        assert len(library.tracks) == 6
        assert playlists == {
            splitext(basename(path_playlist_m3u))[0]: path_playlist_m3u,
            splitext(basename(path_playlist_xautopf_bp))[0]: path_playlist_xautopf_bp,
            splitext(basename(path_playlist_xautopf_ra))[0]: path_playlist_xautopf_ra,
        }

        assert library.last_played == datetime(2023, 11, 9, 11, 22, 33)
        assert library.last_added == datetime(2023, 10, 17, 14, 42, 37)
        assert library.last_modified == max(track.date_modified for track in library.tracks)

        # check that tracks have been enriched using library XML data
        track_mp3: LocalTrack = library[path_track_mp3]
        assert track_mp3.rating == 20
        assert track_mp3.date_added == datetime(2023, 5, 20, 23, 22, 11)
        assert track_mp3.last_played == datetime(2023, 7, 20, 6, 12, 26)
        assert track_mp3.play_count == 5

        track_flac: LocalTrack = library[path_track_flac]
        assert track_flac.rating == 50
        assert track_flac.date_added == datetime(2023, 5, 23, 21, 33, 20)
        assert track_flac.last_played == datetime(2023, 9, 2, 8, 21, 22)
        assert track_flac.play_count == 10

        track_wma: LocalTrack = library[path_track_wma]
        assert track_wma.rating == 40
        assert track_wma.date_added == datetime(2023, 5, 29, 15, 26, 22)
        assert track_wma.last_played == datetime(2023, 5, 30, 22, 57, 24)
        assert track_wma.play_count == 200

    @pytest.mark.parametrize("path", [library_filepath], ["path"])
    def test_save(self, path: str, remote_wrangler: RemoteDataWrangler):
        MusicBee.xml_library_filename = library_filename

        library = MusicBee(
            library_folder=path_resources,
            musicbee_folder=path_library_resources,
            playlist_folder=path_playlist_resources,
            other_folders="../",
            remote_wrangler=remote_wrangler,
        )
        library.load()
        library._xml_parser.path = path
        library.save(dry_run=True)
        original_dt_modified = datetime.fromtimestamp(getmtime(path))

        library.save(dry_run=False)
        assert datetime.fromtimestamp(getmtime(path)) > original_dt_modified

        # these keys fail on other systems, ignore them in line checks
        ignore_keys = ["Music Folder", "Date Modified", "Location"]
        with open(library_filepath, "r") as f_in, open(path, "r") as f_out:
            for line_in, line_out in zip(f_in, f_out):
                if any(f"<key>{key}</key>" in line_in for key in ignore_keys):
                    continue
                assert line_in == line_out
