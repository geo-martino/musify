import os
import shutil
from datetime import datetime
from os.path import basename, splitext, join, dirname, relpath, getmtime, sep
from pathlib import Path

import pytest

from musify.file.exception import FileDoesNotExistError
from musify.file.path_mapper import PathMapper
from musify.libraries.local.library import LocalLibrary, MusicBee
from musify.libraries.local.library.musicbee import XMLLibraryParser, REQUIRED_MODULES
from musify.libraries.local.track import LocalTrack
from musify.libraries.remote.core.processors.wrangle import RemoteDataWrangler
from musify.processors.filter import FilterIncludeExclude, FilterDefinedList
from musify.utils import required_modules_installed
from tests.libraries.local.library.testers import LocalLibraryTester
from tests.libraries.local.track.utils import random_track
from tests.libraries.local.utils import path_library_resources
from tests.libraries.local.utils import path_playlist_m3u, path_playlist_xautopf_bp
from tests.libraries.local.utils import path_playlist_resources, path_playlist_all
from tests.libraries.local.utils import path_track_all, path_track_resources
from tests.libraries.local.utils import path_track_mp3, path_track_flac, path_track_wma
from tests.utils import path_resources

library_xml_filename = "musicbee_library.xml"
library_xml_filepath = join(path_library_resources, library_xml_filename)
settings_xml_filename = "musicbee_settings.ini"
settings_xml_filepath = join(path_library_resources, settings_xml_filename)


@pytest.mark.skipif(not required_modules_installed(REQUIRED_MODULES), reason="required modules not installed.")
class TestMusicBee(LocalLibraryTester):

    @pytest.fixture
    def musicbee_folder(self, tmp_path: Path):
        """
        Formats the MusicBee XML files and copies them to the tmp folder, returning the absolute path to this
        folder to use as the musicbee_folder when instantiating MusicBee library objects.
        """
        tmp_library_path = join(tmp_path, str(relpath(path_library_resources)).lstrip(sep))

        trg_path = join(tmp_library_path, library_xml_filename)
        os.makedirs(dirname(trg_path), exist_ok=True)
        shutil.copyfile(library_xml_filepath, trg_path)

        with open(trg_path, "r") as f:
            data = f.read().format(path_resources=path_resources.replace("\\", "/"))
        with open(trg_path, "w") as f:
            f.write(data)

        trg_path = join(tmp_library_path, basename(settings_xml_filepath))
        os.makedirs(dirname(trg_path), exist_ok=True)
        shutil.copyfile(settings_xml_filepath, trg_path)

        with open(trg_path, "r") as f:
            data = f.read().format(path_resources=path_resources, sep=sep)
        with open(trg_path, "w") as f:
            f.write(data)

        shutil.copytree(path_playlist_resources, join(tmp_library_path, MusicBee.playlists_path))

        MusicBee.xml_library_path = library_xml_filename
        MusicBee.xml_settings_path = settings_xml_filename
        yield tmp_library_path

        shutil.rmtree(tmp_library_path)

    @pytest.fixture
    def library(self, musicbee_folder: str, path_mapper: PathMapper) -> LocalLibrary:
        library = MusicBee(musicbee_folder=musicbee_folder, path_mapper=path_mapper)
        assert library._library_xml_path == join(musicbee_folder, MusicBee.xml_library_path)
        assert library._settings_xml_path == join(musicbee_folder, MusicBee.xml_settings_path)

        library.load()
        # needed to ensure __setitem__ check passes
        library.items.append(random_track(cls=library[0].__class__))
        return library

    def test_parser_library(self, musicbee_folder: str):
        path = join(musicbee_folder, MusicBee.xml_library_path)
        parser = XMLLibraryParser(path=path, path_keys=MusicBee.xml_library_path_keys)

        xml = parser.parse()
        assert xml["Major Version"] == 3
        assert xml["Minor Version"] == 5
        assert xml["Application Version"] == "3.5.8447.35892"
        assert xml["Music Folder"].endswith(relpath(dirname(path_library_resources)).lstrip("./\\"))
        assert xml["Library Persistent ID"] == "3D76B2A6FD362901"
        assert len(xml["Tracks"]) == 6
        assert len(xml["Playlists"]) == 4

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

    def test_init_fails(self, musicbee_folder: str):
        # should load files in certain order, remove each file in reverse load order and test related exception
        settings_path_error = join(musicbee_folder, MusicBee.xml_settings_path)
        os.remove(settings_path_error)
        with pytest.raises(FileDoesNotExistError, match=f".*{settings_path_error.replace('\\', '\\\\')}"):
            MusicBee(musicbee_folder=musicbee_folder)

        library_path_error = join(musicbee_folder, MusicBee.xml_library_path)
        os.remove(library_path_error)
        with pytest.raises(FileDoesNotExistError, match=f".*{library_path_error.replace('\\', '\\\\')}"):
            MusicBee(musicbee_folder=musicbee_folder)

    def test_init_no_playlists(self, musicbee_folder: str):
        # delete all playlists in tmp folder for this run
        shutil.rmtree(join(musicbee_folder, MusicBee.playlists_path))
        library = MusicBee(musicbee_folder=musicbee_folder)

        assert library.library_folders == [path_track_resources, path_playlist_resources]
        assert library._library_xml_path == join(musicbee_folder, library_xml_filename)
        assert all(path in library._track_paths for path in path_track_all)

        assert library.playlist_folder is None
        assert not library.playlists
        assert not library._playlist_paths

    def test_init_include(self, musicbee_folder: str):
        library = MusicBee(
            musicbee_folder=musicbee_folder,
            playlist_filter=FilterDefinedList(
                [splitext(basename(path_playlist_m3u))[0], splitext(basename(path_playlist_xautopf_bp))[0]]
            ),
        )
        assert library.playlist_folder == join(musicbee_folder, MusicBee.playlists_path)
        assert set(library._playlist_paths) == {
            splitext(basename(path_playlist_m3u))[0],
            splitext(basename(path_playlist_xautopf_bp))[0],
        }

    def test_init_exclude(self, musicbee_folder: str):
        library = MusicBee(
            musicbee_folder=musicbee_folder,
            playlist_filter=FilterIncludeExclude(
                include=FilterDefinedList(),
                exclude=FilterDefinedList([splitext(basename(path_playlist_xautopf_bp))[0]])
            ),
        )
        assert library.playlist_folder == join(musicbee_folder, MusicBee.playlists_path)
        assert set(library._playlist_paths) == {
            splitext(basename(path))[0] for path in path_playlist_all if path != path_playlist_xautopf_bp
        }

    def test_load(self, musicbee_folder: str, path_mapper: PathMapper):
        MusicBee.xml_library_filename = library_xml_filename
        library = MusicBee(musicbee_folder=musicbee_folder, path_mapper=path_mapper)
        library.load()

        assert len(library.tracks) == 6
        assert set(library.playlists) == {splitext(basename(path))[0] for path in path_playlist_all}

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

    # noinspection PyTestUnpassedFixture
    def test_save(self, musicbee_folder: str, path_mapper: PathMapper, remote_wrangler: RemoteDataWrangler):
        library = MusicBee(musicbee_folder=musicbee_folder, path_mapper=path_mapper, remote_wrangler=remote_wrangler)
        source_dt_modified = datetime.fromtimestamp(getmtime(library_xml_filepath))
        original_dt_modified = datetime.fromtimestamp(getmtime(library._library_xml_parser.path))

        library.load()
        library.save(dry_run=True)
        assert datetime.fromtimestamp(getmtime(library._library_xml_parser.path)) == original_dt_modified
        assert datetime.fromtimestamp(getmtime(library_xml_filepath)) == source_dt_modified

        library.save(dry_run=False)
        assert datetime.fromtimestamp(getmtime(library._library_xml_parser.path)) > original_dt_modified
        assert datetime.fromtimestamp(getmtime(library_xml_filepath)) == source_dt_modified

        # these keys fail on other systems, ignore them in line checks
        ignore_keys = ["Music Folder", "Date Modified", "Location"]
        with open(library_xml_filepath, "r") as f_in, open(library._library_xml_parser.path, "r") as f_out:
            for i, (line_in, line_out) in enumerate(zip(f_in, f_out)):
                if any(f"<key>{key}</key>" in line_in for key in ignore_keys):
                    continue
                assert line_in == line_out
