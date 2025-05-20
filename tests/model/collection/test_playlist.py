import pytest
from faker import Faker

from musify.model import MusifyModel
from musify.model.collection.playlist import Playlist
from musify.model.item.track import Track


class TestPlaylist:
    @pytest.fixture
    def model(self, faker: Faker) -> MusifyModel:
        return Playlist(name=faker.sentence())

    # def test_merge_input_validation(self, playlist: Playlist, collection_merge_invalid: Iterable[MusifyResource]):
    #     with pytest.raises(MusifyTypeError):
    #         playlist.merge(collection_merge_invalid)
    #
    # def test_merge(self, playlist: Playlist):
    #     initial_count = len(playlist)
    #     items = [item for item in collection_merge_items]
    #
    #     playlist.merge([items[0]])
    #     assert len(playlist) == initial_count + 1
    #     assert playlist[-1] == items[0]
    #
    #     playlist.merge(playlist.items + items[:-1])
    #     assert len(playlist) == initial_count + len(items) - 1
    #
    #     playlist.merge(playlist.items + items)
    #     assert len(playlist) == initial_count + len(items)
    #
    # def test_merge_with_reference(self, playlist: Playlist):
    #     # setup collections so 2 items are always removed and many items are always added
    #     reference = deepcopy(playlist)
    #     reference_items = sample(reference.items, k=(len(reference.items) // 2) + 1)
    #     reference.clear()
    #     reference.extend(reference_items)
    #     assert len(reference) >= 3
    #
    #     other = [item for item in collection_merge_items]
    #     other.extend(reference[:2])  # both other and playlist have item 0, playlist does not have item 1
    #     other.extend(reference[3:])  # both other and playlist has items 3+
    #
    #     playlist_items = [item for item in playlist if item not in reference]
    #     playlist.clear()
    #     playlist.extend(playlist_items)
    #     playlist.append(reference[0])  # both other and playlist have item 0
    #     playlist.extend(reference[2:])  # playlist has item 2, both other and playlist has items 3+
    #     playlist.append(next(item for item in other if item not in reference and item not in playlist))
    #
    #     removed = [item for item in reference if item not in other or item not in playlist]
    #     assert len(removed) >= 2
    #
    #     added = [item for item in other if item not in reference]
    #     added += [item for item in playlist if item not in reference and item not in added]
    #     assert added
    #
    #     playlist.merge(other=other, reference=reference)
    #     assert all(item not in playlist for item in removed)
    #     assert all(item in playlist for item in added)
    #     assert len(playlist) == len(reference) - len(removed) + len(added)
    #
    # def test_merge_dunder_methods(self, playlist: Playlist):
    #     initial_count = len(playlist)
    #     other = deepcopy(playlist)
    #     other.tracks.clear()
    #     other.tracks.extend(collection_merge_items)
    #
    #     new_pl = playlist | other
    #     assert len(new_pl) == initial_count + len(other)
    #     assert new_pl[initial_count:] == other.items
    #     assert len(playlist) == initial_count
    #
    #     playlist |= other
    #     assert len(playlist) == initial_count + len(other)
    #     assert playlist[initial_count:] == other.items
