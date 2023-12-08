import os
import shutil
from datetime import datetime
from os.path import basename, splitext, join, exists, dirname, relpath

import pytest

from syncify.local.exception import MusicBeeError
from syncify.local.library.musicbee import MusicBee, XMLLibraryParser
from syncify.local.track import LocalTrack
from tests import path_resources
from tests.abstract.misc import pretty_printer_tests
from tests.local import remote_wrangler
from tests.local.library import init_blank_test
from tests.local.library import path_library_resources, path_library_cache
from tests.local.playlist import path_playlist_resources, path_playlist_m3u
from tests.local.playlist import path_playlist_xautopf_bp, path_playlist_xautopf_ra
from tests.local.track import path_track_resources, path_track_all, path_track_mp3, path_track_flac, path_track_wma

library_filename = "musicbee_library.xml"
library_filepath = join(path_library_resources, library_filename)


def test_parser():
    parser_filepath = join(path_library_cache, "parser_test.xml")
    os.makedirs(dirname(parser_filepath), exist_ok=True)
    shutil.copyfile(library_filepath, parser_filepath)

    parser = XMLLibraryParser(path=parser_filepath, path_keys=MusicBee.xml_path_keys)

    xml = parser.parse()
    assert xml["Major Version"] == 3
    assert xml["Minor Version"] == 5
    assert xml["Application Version"] == "3.5.8447.35892"
    print(xml["Music Folder"], path_library_resources, relpath(dirname(path_library_resources)).lstrip("./\\"))
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

    os.remove(parser_filepath)


def test_init():
    with pytest.raises(FileNotFoundError, match="MusicBee"):
        MusicBee(load=False)

    with pytest.raises(MusicBeeError):
        MusicBee(musicbee_folder=None, load=False)

    library_path_error = join(path_library_resources, "MusicBee")
    with pytest.raises(FileNotFoundError, match=f".*{library_path_error.replace('\\', '\\\\')}"):
        MusicBee(library_folder=path_library_resources, load=False)

    assert MusicBee.xml_library_filename != library_filename
    library_path_error = join(path_library_resources, MusicBee.xml_library_filename)
    with pytest.raises(FileNotFoundError, match=f".*{library_path_error.replace('\\', '\\\\')}"):
        MusicBee(musicbee_folder=path_library_resources, load=False)

    MusicBee.xml_library_filename = library_filename
    library_blank = MusicBee(musicbee_folder=path_library_resources, load=False)
    init_blank_test(library_blank)
    assert library_blank._path == library_filepath

    library_no_playlists = MusicBee(
        library_folder=path_resources,
        musicbee_folder=basename(path_library_resources),
        playlist_folder="does_not_exist",
        load=False
    )
    assert library_no_playlists.library_folder == path_resources
    assert library_blank._path == library_filepath
    assert all(path in library_no_playlists._track_paths for path in path_track_all)
    assert library_no_playlists.playlist_folder is None

    pretty_printer_tests(library_no_playlists, dict_json_equal=False)

    library_include = MusicBee(
        library_folder=path_resources,
        musicbee_folder=basename(path_library_resources),
        playlist_folder=basename(path_playlist_resources),
        include=[splitext(basename(path_playlist_m3u))[0], splitext(basename(path_playlist_xautopf_bp))[0]],
        load=False
    )
    assert library_include.playlist_folder == path_playlist_resources
    assert library_include._playlist_paths == {
        splitext(basename(path_playlist_m3u).casefold())[0]: path_playlist_m3u,
        splitext(basename(path_playlist_xautopf_bp).casefold())[0]: path_playlist_xautopf_bp,
    }

    pretty_printer_tests(library_include, dict_json_equal=False)

    library_exclude = MusicBee(
        library_folder=path_resources,
        musicbee_folder=basename(path_library_resources),
        playlist_folder=basename(path_playlist_resources),
        exclude=[splitext(basename(path_playlist_xautopf_bp))[0]],
        load=False
    )
    assert library_exclude.playlist_folder == path_playlist_resources
    assert library_exclude._playlist_paths == {
        splitext(basename(path_playlist_m3u).casefold())[0]: path_playlist_m3u,
        splitext(basename(path_playlist_xautopf_ra).casefold())[0]: path_playlist_xautopf_ra,
    }

    pretty_printer_tests(library_exclude, dict_json_equal=False)


# noinspection PyTypeChecker
def test_load():
    MusicBee.xml_library_filename = library_filename
    library = MusicBee(
        library_folder=path_track_resources,
        musicbee_folder=path_library_resources,
        playlist_folder=path_playlist_resources,
    )
    tracks = {track.path for track in library.tracks}
    playlists = {name: pl.path for name, pl in library.playlists.items()}

    assert tracks == path_track_all
    assert playlists == {
        splitext(basename(path_playlist_m3u))[0]: path_playlist_m3u,
        splitext(basename(path_playlist_xautopf_bp))[0]: path_playlist_xautopf_bp,
        splitext(basename(path_playlist_xautopf_ra))[0]: path_playlist_xautopf_ra,
    }

    assert library.last_played == datetime(2023, 11, 1, 15, 11, 11)
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


def test_save():
    path_output_xml = join(path_library_cache, "musicbee_library_save_test.xml")
    if exists(path_output_xml):
        os.remove(path_output_xml)
    os.makedirs(dirname(path_output_xml), exist_ok=True)
    MusicBee.xml_library_filename = library_filename

    library = MusicBee(
        library_folder=path_resources,
        musicbee_folder=path_library_resources,
        playlist_folder=path_playlist_resources,
        other_folders="../",
        remote_wrangler=remote_wrangler,
    )
    library._xml_parser.path = path_output_xml
    library.save(dry_run=True)
    assert not exists(path_output_xml)

    library.save(dry_run=False)
    assert exists(path_output_xml)

    with open(path_output_xml, "r") as f:
        print(f.read())

    with open(library_filepath, "r") as f:
        print(f.read())

    with open(library_filepath, "r") as f_in, open(path_output_xml, "r") as f_out:
        for line_in, line_out in zip(f_in, f_out):
            if ">Music Folder<" in line_in:  # fails on other systems so skip
                continue
            assert line_in == line_out

    os.remove(path_output_xml)
