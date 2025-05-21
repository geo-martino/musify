from datetime import date
from io import BytesIO
from random import choice

import numpy
import pytest
from PIL import Image
from aioresponses import aioresponses, CallbackResult
from faker import Faker
from pydantic import TypeAdapter

from musify.exception import MusifyValueError
from musify.model import MusifyModel, MusifyRootModel
from musify.model.properties import HasName, HasSeparableTags, Position, Length, SparseDate, KeySignature, ImageLink, \
    RemoteURI, HasURI, HasMutableURI
from tests.model.conftest import SimpleURI
from tests.model.testers import MusifyModelTester, MusifyResourceTester, UniqueKeyTester


class TestHasName(MusifyResourceTester):
    @pytest.fixture
    def model(self) -> MusifyModel:
        return HasName(name="Test Name")

    def test_from_name(self, faker: Faker):
        name = faker.word()
        model = TypeAdapter(HasName).validate_python(name)
        assert model.name == name

    def test_rich_comparison_dunder_methods(self) -> None:
        assert HasName(name="Test Name") < HasName(name="Zest Name")
        assert HasName(name="Test Name") <= HasName(name="Zest Name")
        assert HasName(name="Test Name") > HasName(name="Rest Name")
        assert HasName(name="Test Name") >= HasName(name="Rest Name")


class TestHasSeparableTags(MusifyResourceTester):
    @pytest.fixture
    def model(self) -> MusifyModel:
        return HasSeparableTags()

    def test_join_tags(self) -> None:
        tags = ["tag1", "tag2", "tag3"]
        assert HasSeparableTags._join_tags(tags) == HasSeparableTags._tag_sep.join(tags)

    def test_separate_tags(self) -> None:
        tags = ["tag1", "tag2", "tag3"]
        tag_string = HasSeparableTags._tag_sep.join(tags)
        assert HasSeparableTags._separate_tags(tag_string) == tags


class TestRemoteURI(MusifyModelTester):
    @pytest.fixture
    def model(self, uri: SimpleURI) -> MusifyRootModel:
        return uri

    def test_marks_existence(self, model: SimpleURI) -> None:
        assert model._unavailable_id not in str(model)
        assert model.exists

        model = SimpleURI(":".join((model.source, model.type, model._unavailable_id)))
        assert model._unavailable_id in str(model)
        assert not model.exists

    def test_equality(self, model: SimpleURI):
        assert model == model
        assert model == str(model)
        assert model == SimpleURI(str(model))

        assert model != SimpleURI(":".join((model.source, model.type, "different_id")))
        assert model != SimpleURI(":".join((model.source, "different_type", model.id)))

        assert model == model.id
        assert model != SimpleURI(":".join((model.source, model.type, "different_id"))).id

        assert model == model.url
        assert model != SimpleURI(":".join((model.source, "different_type", model.id))).url

        assert model == model.href
        assert model != SimpleURI(":".join((model.source, "different_type", model.id))).href


class TestHasURI(UniqueKeyTester):
    @pytest.fixture
    def model(self, uri: RemoteURI) -> MusifyModel:
        return HasURI(uri=uri)

    def test_uri_field_is_read_only(self, model: HasURI, uri: RemoteURI) -> None:
        assert model.uri is uri

        with pytest.raises(AttributeError):
            # noinspection PyPropertyAccess
            model.uri = uri

    def test_equality(self, model: HasURI, uri: RemoteURI):
        assert model == model
        assert model == HasURI(uri=uri)

        # doesn't match on string values
        assert model != str(uri)
        assert model != uri.id
        assert model != uri.href
        assert model != uri.url


class TestHasMutableURI(UniqueKeyTester):
    @pytest.fixture
    def model(self, uris: list[RemoteURI]) -> MusifyModel:
        return HasMutableURI(source=choice(uris).source, uris=uris)

    def test_validates_uris_are_from_unique_sources(self, uris: list[RemoteURI]):
        uri = choice(uris)
        different_uri = next(u for u in uris if u.source != uri.source)
        new_uri = SimpleURI.from_id(different_uri.id, different_uri.type, uri.source)

        HasMutableURI(uris=uris)
        with pytest.raises(ValueError):
            HasMutableURI(uris=[*uris, new_uri])

    def test_get_uri(self, model: HasMutableURI, uris: list[RemoteURI]) -> None:
        assert model.uris == uris
        assert model.uri.source == model.source
        assert model.uri == next(uri for uri in uris if uri.source == model.source)

        model.source = None
        assert model.uri is None

    def test_set_uri(self, model: HasMutableURI, uris: list[RemoteURI]):
        assert model.uri is not None

        old_uri = model.uri
        different_uri = next(uri for uri in uris if uri.source != model.source)
        new_uri = SimpleURI.from_id(different_uri.id, different_uri.type, model.uri.source)
        assert new_uri not in model.unique_keys

        model.uri = new_uri
        assert model.uri is new_uri
        assert new_uri in model.uris
        assert new_uri in model.unique_keys
        assert old_uri not in model.uris
        assert old_uri not in model.unique_keys

    def test_set_uri_validates_type(self, model: HasMutableURI, uris: list[RemoteURI]):
        different_uri = next(uri for uri in uris if uri.source != model.source)

        with pytest.raises(MusifyValueError):
            model.uri = str(model.uri)
        with pytest.raises(MusifyValueError):
            model.uri = different_uri

    def test_delete_uri(self, model: HasMutableURI, uris: list[RemoteURI]):
        uri = model.uri
        del model.uri
        assert uri not in model.uris

    # noinspection PyTestUnpassedFixture
    def test_has_uri(self, model: HasMutableURI, uris: list[RemoteURI]) -> None:
        assert model.uri.exists
        assert model.has_uri is True

        uri = SimpleURI.from_id(model.uri._unavailable_id, model.uri.type, model.source)
        model.uri = uri
        assert model.uri is None
        assert model.has_uri is False

        del model.uri
        assert model.uri is None
        assert model.has_uri is None

    def test_equality(self, model: HasMutableURI, uris: list[RemoteURI]) -> None:
        assert model == model
        assert model == HasMutableURI(source=model.source, uris=uris)

        # URIs do not match
        missing_uri = next(uri for uri in uris if uri.source != model.source)
        assert model != HasMutableURI(source=missing_uri.source, uris=uris)

        # 2nd model doesn't have a URI set due to no URIs matching the given source)
        missing_uri = next(uri for uri in uris if uri.source != model.source)
        assert model != HasMutableURI(source=missing_uri.source, uris=[uri for uri in uris if uri is not missing_uri])


class TestPosition(MusifyModelTester):
    @pytest.fixture
    def model(self) -> MusifyModel:
        return Position()

    def test_from_number(self, faker: Faker):
        number = faker.random_int(1, 10)
        model = TypeAdapter(Position).validate_python(number)
        assert model.number == number
        assert model.total is None

    def test_number_cannot_exceed_total(self, model: Position) -> None:
        model.total = 5
        with pytest.raises(ValueError):
            model.number = model.total + 1

        with pytest.raises(ValueError):
            Position(number=5, total=4)


class TestLength(MusifyModelTester):
    @pytest.fixture
    def model(self, faker: Faker) -> MusifyRootModel:
        return Length(faker.random_int())

    def test_numeric_representation_conversion(self, model: Length) -> None:
        model.root = "12"
        assert int(model) == 12

        model.root = "12.3456"
        assert float(model) == 12.3456

        model.root = "12:34"
        assert int(model) == 12 * 60 + 34

        model.root = "260:12:34"
        assert int(model) == 260 * 60 * 60 + 12 * 60 + 34

        model.root = "12:34.123456"
        assert float(model) == 12 * 60 + 34 + 0.123456

    def test_numeric_representation_conversion_fails(self, model: Length) -> None:
        with pytest.raises(ValueError):
            model.root = "12:34:56:78"
        with pytest.raises(ValueError):
            model.root = "ab:cd"

    def test_number_conversion(self, model: Length) -> None:
        model.root = 123.45
        assert int(model) == 123

        model.root = 123
        assert float(model) == 123.0


class TestRating(MusifyModelTester):
    pass


class TestSparseDate(MusifyModelTester):
    @pytest.fixture
    def model(self, faker: Faker) -> MusifyModel:
        return SparseDate(year=faker.year())

    def test_date_property(self, model: SparseDate, faker: Faker) -> None:
        model.month = None
        model.day = None
        assert model.date is None

        model.day = faker.random_int(min=1, max=28)
        assert model.date is None

        model.month = faker.random_int(min=1, max=12)
        assert model.date == date(year=model.year, month=model.month, day=model.day)


class TestImageLink(MusifyModelTester):
    @pytest.fixture
    def model(self, faker: Faker) -> MusifyModel:
        # noinspection PyProtectedMember
        return ImageLink(
            url=faker.url(),
            kind="Cover Front",
            height=faker.random_int(min=600, max=1000),
            width=faker.random_int(min=600, max=1000),
        )

    def test_equality(self, model: ImageLink, faker: Faker) -> None:
        assert model == model
        assert model == ImageLink(
            url=model.url, kind=model.kind, height=faker.random_int(), width=faker.random_int(),
        )

        assert model != ImageLink(
            url=model.url, kind="A different kind", height=faker.random_int(), width=faker.random_int(),
        )
        assert model != ImageLink(
            url=faker.url(), kind=model.kind, height=faker.random_int(), width=faker.random_int(),
        )

    def test_rich_comparison_dunder_methods(self, model: ImageLink, faker: Faker) -> None:
        assert model < ImageLink(
            url=faker.url(), kind=model.kind, height=model.height + 100, width=model.width + 100,
        )
        assert model <= ImageLink(
            url=faker.url(), kind=model.kind, height=model.height + 100, width=model.width,
        )
        assert model <= ImageLink(
            url=faker.url(), kind=model.kind, height=model.height, width=model.width,
        )

        assert model > ImageLink(
            url=faker.url(), kind=model.kind, height=model.height - 100, width=model.width - 100,
        )
        assert model >= ImageLink(
            url=faker.url(), kind=model.kind, height=model.height - 100, width=model.width,
        )
        assert model >= ImageLink(
            url=faker.url(), kind=model.kind, height=model.height, width=model.width,
        )

    async def test_load(self, model: ImageLink, mock_response: aioresponses) -> None:
        body = BytesIO()
        img_array = numpy.random.rand(100, 100, 3) * 255
        img = Image.fromarray(img_array.astype("uint8")).convert("RGBA")
        img.save(body, format="PNG")

        mock_response.get(
            model.url,
            callback=lambda *_, **__: CallbackResult(method="GET", body=body.getvalue()),
        )
        assert (await model.load()).tobytes() == img.tobytes()


class TestKeySignature(MusifyModelTester):
    @pytest.fixture
    def model(self, faker: Faker) -> MusifyModel:
        # noinspection PyProtectedMember
        return KeySignature(
            root=faker.random_int(min=0, max=len(KeySignature._root_notes) - 1),
            mode=faker.boolean(),
        )

    def test_key_property(self, model: KeySignature) -> None:
        model.root = 5
        model.mode = False
        assert model.key == str(model) == "F"

        model.mode = True
        assert model.key == str(model) == "Fm"

    def test_set_by_key_signature(self, model: KeySignature) -> None:
        model.mode = False
        model.root = "Gm"
        assert model.root == 7
        assert not model.mode  # remains unchanged

        model.mode = "Am"
        assert model.root == 7  # remains unchanged
        assert model.mode

        model.key = "Cm"
        assert model.root == 0
        assert model.mode

