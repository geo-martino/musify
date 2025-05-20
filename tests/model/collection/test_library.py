class TestLibrary:
    """
    Run generic tests for :py:class:`Library` implementations.
    The collection must have 3 or more playlists and all playlists must be unique.
    """
    #
    # @abstractmethod
    # def library(self, *args, **kwargs) -> Library:
    #     """Yields a loaded :py:class:`Library` object to be tested as pytest.fixture."""
    #     raise NotImplementedError
    #
    # @pytest.fixture
    # def collection(self, library: Library) -> MusifyCollection:
    #     return library
    #
    # @staticmethod
    # def assert_merge_playlists(
    #         library: Library,
    #         test: Any,
    #         extend_playlists: Iterable[Playlist] = (),
    #         new_playlists: Iterable[Playlist] = ()
    # ):
    #     """Run merge playlists function on ``source`` library against ``test_values`` and assert expected results"""
    #     # fine-grained merge functionality is tested in the playlist tester
    #     # we just need to assert the playlist was modified in some way
    #     original_playlists = deepcopy(library.playlists)
    #     library.merge_playlists(test)
    #
    #     test_names = {pl.name for pl in extend_playlists} | {pl.name for pl in new_playlists}
    #     for pl in library.playlists.values():  # test unchanged playlists are unchanged
    #         if pl.name in test_names:
    #             continue
    #         assert library.playlists[pl.name].tracks == pl.tracks
    #
    #     for pl in extend_playlists:
    #         assert library.playlists[pl.name].tracks != original_playlists[pl.name].tracks
    #         assert library.playlists[pl.name].tracks == pl.tracks
    #
    #     for pl in new_playlists:
    #         assert pl.name not in original_playlists
    #         assert library.playlists[pl.name].tracks == pl.tracks
    #         assert id(library.playlists[pl.name]) != id(pl)  # deepcopy occurred
    #
    # @pytest.fixture
    # def merge_playlists(self, library: Library) -> list[Playlist]:
    #     """Set of playlists to be used in ``merge_playlists`` tests."""
    #     # playlist order: extend, create, unchanged
    #     return deepcopy(sample(list(library.playlists.values()), k=3))
    #
    # @pytest.fixture
    # def merge_playlists_extend(
    #         self, library: Library, merge_playlists: list[Playlist], collection_merge_items: Iterable[MusifyResource]
    # ) -> list[Playlist]:
    #     """Set of playlists that already exist in the ``library`` with extra tracks to be merged"""
    #     merge_playlist = merge_playlists[0]
    #     merge_playlist.extend(collection_merge_items)
    #     assert merge_playlist.tracks != library.playlists[merge_playlist.name].tracks
    #
    #     return [merge_playlist]
    #
    # @pytest.fixture
    # def merge_playlists_new(self, library: Library, merge_playlists: list[Playlist]) -> list[Playlist]:
    #     """Set of new playlists to merge with the given ``library``"""
    #     new_playlist = merge_playlists[1]
    #     library.playlists.pop(new_playlist.name)
    #     assert new_playlist.name not in library.playlists
    #
    #     return [new_playlist]
    #
    # def test_merge_playlists_as_collection(
    #         self,
    #         library: Library,
    #         merge_playlists: list[Playlist],
    #         merge_playlists_extend: list[Playlist],
    #         merge_playlists_new: list[Playlist],
    # ):
    #     self.assert_merge_playlists(
    #         library=library,
    #         test=merge_playlists,  # Collection[Playlist]
    #         extend_playlists=merge_playlists_extend,
    #         new_playlists=merge_playlists_new
    #     )
    #
    # def test_merge_playlists_as_mapping(
    #         self,
    #         library: Library,
    #         merge_playlists: list[Playlist],
    #         merge_playlists_extend: list[Playlist],
    #         merge_playlists_new: list[Playlist],
    # ):
    #     self.assert_merge_playlists(
    #         library=library,
    #         test={pl.name: pl for pl in merge_playlists},  # Mapping[str, Playlist]
    #         extend_playlists=merge_playlists_extend,
    #         new_playlists=merge_playlists_new
    #     )
    #
    # def test_merge_playlists_as_library(
    #         self,
    #         library: Library,
    #         merge_playlists: list[Playlist],
    #         merge_playlists_extend: list[Playlist],
    #         merge_playlists_new: list[Playlist],
    # ):
    #     test = deepcopy(library)
    #     test.playlists.clear()
    #     test.playlists.update({pl.name: pl for pl in merge_playlists})
    #
    #     self.assert_merge_playlists(
    #         library=library, test=test, extend_playlists=merge_playlists_extend, new_playlists=merge_playlists_new
    #     )
