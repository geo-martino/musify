from abc import ABCMeta, abstractmethod
from collections.abc import Collection, Mapping
from copy import copy, deepcopy
from typing import Any

from syncify.shared.core.base import Item
from syncify.shared.core.object import Playlist
from syncify.shared.remote.library import RemoteLibrary
from syncify.shared.remote.object import RemoteTrack
from tests.shared.core.collection import LibraryTester
from tests.local.track.utils import random_tracks
from tests.shared.remote.object import RemoteCollectionTester
from tests.shared.remote.utils import RemoteMock


class RemoteLibraryTester(RemoteCollectionTester, LibraryTester, metaclass=ABCMeta):

    @abstractmethod
    def collection_merge_items(self, *args, **kwargs) -> list[RemoteTrack]:
        """
        Yields an Iterable of :py:class:`RemoteTrack` for use in :py:class:`ItemCollection` tests as pytest.fixture.
        This must be a valid set of tracks that can be successfully called by the api_mock fixture.
        """
        raise NotImplementedError

    @staticmethod
    def test_load_playlists(library_unloaded: RemoteLibrary):
        library_unloaded.load_playlists()

        # only loaded playlists matching the filter
        assert len(library_unloaded.playlists) == 10

        # all playlist tracks were added to the stored library tracks
        unique_tracks_count = len(set(track for pl in library_unloaded.playlists.values() for track in pl))
        assert len(library_unloaded.tracks_in_playlists) == unique_tracks_count

        # does not add duplicates to the loaded lists
        library_unloaded.load_playlists()
        assert len(library_unloaded.playlists) == 10
        assert len(library_unloaded.tracks_in_playlists) == unique_tracks_count

    @abstractmethod
    def test_load_tracks(self, *_, **__):
        raise NotImplementedError

    @abstractmethod
    def test_load_saved_albums(self, *_, **__):
        raise NotImplementedError

    @abstractmethod
    def test_load_saved_artists(self, *_, **__):
        raise NotImplementedError

    @staticmethod
    def test_load(library_unloaded: RemoteLibrary):
        assert not library_unloaded.playlists
        assert not library_unloaded.tracks
        assert not library_unloaded.albums
        assert not library_unloaded.artists

        library_unloaded.load()
        assert library_unloaded.playlists
        assert library_unloaded.tracks
        assert library_unloaded.albums
        assert library_unloaded.artists

    def test_enrich_tracks(self, library: RemoteLibrary, *_, **__):
        """
        This function and related test can be implemented by child classes.
        Just check it doesn't fail for the base test class.
        """
        assert library.enrich_tracks() is None

    def test_enrich_saved_artists(self, library: RemoteLibrary, *_, **__):
        """
        This function and related test can be implemented by child classes.
        Just check it doesn't fail for the base test class.
        """
        assert library.enrich_saved_artists() is None

    def test_enrich_saved_albums(self, library: RemoteLibrary, *_, **__):
        """
        This function and related test can be implemented by child classes.
        Just check it doesn't fail for the base test class.
        """
        assert library.enrich_saved_albums() is None

    @staticmethod
    def test_extend(library: RemoteLibrary, collection_merge_items: list[RemoteTrack], api_mock: RemoteMock):
        api_mock.reset_mock()  # test checks the number of requests made

        # extend on already existing tracks with duplicates not allowed
        library_tracks_start = copy(library.tracks)
        tracks_existing = library.tracks[:10]
        assert len(tracks_existing) > 0

        library.extend(tracks_existing, allow_duplicates=False)
        assert len(library) == len(library_tracks_start)  # no change
        assert len(api_mock.request_history) == 0  # no requests made

        library.extend(collection_merge_items + tracks_existing, allow_duplicates=False)
        assert len(library) == len(library_tracks_start) + len(collection_merge_items)
        assert len(api_mock.request_history) == 0  # no requests made

        library.extend(tracks_existing, allow_duplicates=True)
        assert len(library) == len(library_tracks_start) + len(collection_merge_items) + len(tracks_existing)
        assert len(api_mock.request_history) == 0  # no requests made

        library._tracks = copy(library_tracks_start)
        local_tracks = random_tracks(len(collection_merge_items))
        for remote, local in zip(collection_merge_items, local_tracks):
            local.uri = remote.uri
            assert remote not in library
            assert local not in library

        library.extend(local_tracks)
        assert len(library) == len(library_tracks_start) + len(local_tracks)
        assert len(api_mock.request_history) > 0  # new requests were made

    @staticmethod
    def test_backup(library: RemoteLibrary):
        expected = {name: [track.uri for track in pl] for name, pl in library.playlists.items()}
        assert library.backup_playlists() == expected

    @staticmethod
    def assert_restore(library: RemoteLibrary, backup: Any):
        """Run test and assertions on restore_playlists functionality for given input backup data type"""
        backup_check: Mapping[str, list[str]]
        if isinstance(backup, RemoteLibrary):  # get URIs from playlists in library
            backup_check = {name: [track.uri for track in pl] for name, pl in backup.playlists.items()}
        elif isinstance(backup, Mapping) and all(isinstance(v, Item) for vals in backup.values() for v in vals):
            # get URIs from playlists in map values
            backup_check = {name: [track.uri for track in pl] for name, pl in backup.items()}
        elif not isinstance(backup, Mapping) and isinstance(backup, Collection):
            # get URIs from playlists in collection
            backup_check = {pl.name: [track.uri for track in pl] for pl in backup}
        else:
            backup_check = backup

        name_actual = next(name for name in backup_check if name in library.playlists)
        name_new = next(name for name in backup_check if name not in library.playlists)

        library_test = deepcopy(library)
        library_test.restore_playlists(playlists=backup, dry_run=False)
        assert len(library_test.playlists[name_actual]) == len(backup_check[name_actual])
        # TODO: figure out why this occasionally fails
        assert len(library_test.playlists[name_actual]) != len(library.playlists[name_actual])

        assert name_new in library_test.playlists
        pl_new = library_test.playlists[name_new]
        assert len(pl_new) == len(backup_check[name_new])
        assert library.api.handler.get(pl_new.url)  # new playlist was created and is callable

    def test_restore(self, library: RemoteLibrary, collection_merge_items: list[RemoteTrack]):
        name_actual, pl_actual = next((name, pl) for name, pl in library.playlists.items() if len(pl) > 10)
        name_new = "new playlist"

        # check test parameters are valid
        assert name_new not in library.playlists
        for track in collection_merge_items:
            assert track not in pl_actual

        # dry run
        new_uri_list = [track.uri for track in collection_merge_items]
        backup_uri = {name_new: new_uri_list, "random new name": new_uri_list}
        library_test = deepcopy(library)
        library_test.restore_playlists(playlists=backup_uri, dry_run=True)
        assert len(library_test.playlists) == len(library.playlists)  # no new playlists created/added

        # Mapping[str, Iterable[str]]
        backup_uri = {
            name_actual: [track.uri for track in pl_actual[:5]] + new_uri_list,
            name_new: new_uri_list,
        }
        self.assert_restore(library=library, backup=backup_uri)

        # Mapping[str, Iterable[Track]]
        backup_tracks = {
            name_actual: pl_actual[:5] + collection_merge_items,
            name_new: collection_merge_items,
        }
        self.assert_restore(library=library, backup=backup_tracks)

        # Library
        backup_library = deepcopy(library)
        backup_library.restore_playlists(playlists=backup_uri, dry_run=False)
        self.assert_restore(library=library, backup=backup_library)

        # Collection[Playlist]
        backup_pl = [backup_library.playlists[name_actual], backup_library.playlists[name_new]]
        self.assert_restore(library=library, backup=backup_pl)

    @staticmethod
    def assert_sync(library: RemoteLibrary, playlists: Any, api_mock: RemoteMock):
        """Run test and assertions on library sync functionality for given input playlists data type"""
        playlists_check: Mapping[str, Collection[Item]]
        if isinstance(playlists, RemoteLibrary):  # get map of playlists from the given library
            playlists_check = playlists.playlists
        elif isinstance(playlists, Collection) and all(isinstance(pl, Playlist) for pl in playlists):
            # reformat list to map
            playlists_check = {pl.name: pl for pl in playlists}
        else:
            playlists_check = playlists

        name_actual = next(name for name in playlists_check if name in library.playlists)
        name_new = next(name for name in playlists_check if name not in library.playlists)

        api_mock.reset_mock()
        library_test = deepcopy(library)
        results = library_test.sync(playlists=playlists, dry_run=False)

        # existing playlist assertions
        assert results[name_actual].added == len(playlists_check[name_new])
        assert results[name_actual].removed == 0
        assert results[name_actual].unchanged == len(library.playlists[name_actual])

        url = library_test.playlists[name_actual].url
        requests = [req for req in api_mock.get_requests(method="POST") if req.url.startswith(url)]
        assert len(requests) > 0

        # new playlist assertions
        assert name_new in library_test.playlists
        assert results[name_new].added == len(playlists_check[name_new])
        assert results[name_new].removed == 0
        assert results[name_new].unchanged == 0
        assert library.api.handler.get(library_test.playlists[name_new].url)  # new playlist was created and is callable

        url = library_test.playlists[name_new].url
        requests = [req for req in api_mock.get_requests(method="POST") if req.url.startswith(url)]
        assert len(requests) > 0

    # TODO: figure out why the 'actual' playlist in this test is sometimes un-writeable
    def test_sync(
            self, library: RemoteLibrary, collection_merge_items: list[RemoteTrack], api_mock: RemoteMock
    ):

        name_actual, pl_actual = next((name, pl) for name, pl in library.playlists.items() if len(pl) > 10)
        name_new = "new playlist"

        # check test parameters are valid
        assert name_new not in library.playlists
        for track in collection_merge_items:
            assert track not in pl_actual

        # Mapping[str, Iterable[Item]]
        playlists_tracks = {
            name_actual: pl_actual[:5] + collection_merge_items,
            name_new: collection_merge_items,
        }
        self.assert_sync(library=library, playlists=playlists_tracks, api_mock=api_mock)

        # Library
        playlists_library = deepcopy(library)
        playlists_library.restore_playlists(playlists=playlists_tracks, dry_run=False)
        for name in list(playlists_library.playlists.keys()):
            if name not in playlists_tracks:
                playlists_library.playlists.pop(name)
        self.assert_sync(library=library, playlists=playlists_library, api_mock=api_mock)

        # Collection[Playlist]
        playlists_coll = [playlists_library.playlists[name_actual], playlists_library.playlists[name_new]]
        self.assert_sync(library=library, playlists=playlists_coll, api_mock=api_mock)
