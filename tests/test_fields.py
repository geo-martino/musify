from syncify.abstract.collection import Playlist, Folder, Artist, Album
from syncify.abstract.item import Track, Artist as ArtistItem
from syncify.fields import TrackField, LocalTrackField, ArtistField, ArtistItemField, PlaylistField, FolderField, \
    AlbumField
from syncify.local.track import LocalTrack

from tests.abstract.enums import gets_field_from_name_and_value, check_values_match, tag_field_gives_valid_tags, \
    check_all_fields_are_valid


def test_fields():
    # track TagFields
    gets_field_from_name_and_value(TrackField)
    check_values_match(TrackField)
    tag_field_gives_valid_tags(TrackField)
    assert TrackField.TRACK.to_tag() == {"track_number", "track_total"}
    assert TrackField.DISC.to_tag() == {"disc_number", "disc_total"}
    check_all_fields_are_valid(TrackField, Track, ignore={TrackField.IMAGES})

    gets_field_from_name_and_value(LocalTrackField)
    check_values_match(LocalTrackField)
    tag_field_gives_valid_tags(LocalTrackField)
    assert LocalTrackField.TRACK.to_tag() == {"track_number", "track_total"}
    assert LocalTrackField.DISC.to_tag() == {"disc_number", "disc_total"}
    check_all_fields_are_valid(LocalTrackField, LocalTrack, ignore={LocalTrackField.IMAGES})

    # artist TagFields
    gets_field_from_name_and_value(ArtistItemField)
    check_values_match(ArtistItemField)
    tag_field_gives_valid_tags(ArtistItemField)
    check_all_fields_are_valid(ArtistItemField, ArtistItem, ignore={ArtistItemField.IMAGES})

    # playlist Fields
    gets_field_from_name_and_value(PlaylistField)
    check_values_match(PlaylistField)
    check_all_fields_are_valid(PlaylistField, Playlist, ignore={PlaylistField.IMAGES})

    # folder Fields
    gets_field_from_name_and_value(FolderField)
    check_values_match(FolderField)
    check_all_fields_are_valid(FolderField, Folder, ignore={FolderField.IMAGES})

    # album Fields
    gets_field_from_name_and_value(AlbumField)
    check_values_match(AlbumField)
    check_all_fields_are_valid(AlbumField, Album, ignore={AlbumField.IMAGES})

    # artist Fields
    gets_field_from_name_and_value(ArtistField)
    check_values_match(ArtistField)
    check_all_fields_are_valid(ArtistField, Artist, ignore={ArtistField.IMAGES})
