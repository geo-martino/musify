from collections.abc import Iterable
from random import choice, randrange

from syncify.remote.enums import RemoteIDType, RemoteObjectType
from syncify.remote.processors.wrangle import RemoteDataWrangler
from tests.spotify.utils import random_id, random_ids
from tests.utils import random_str

ALL_ID_TYPES = RemoteIDType.all()
ALL_ITEM_TYPES = RemoteObjectType.all()


def random_id_type(wrangler: RemoteDataWrangler, kind: RemoteObjectType, id_: str = random_id()) -> str:
    """Convert the given ``id_`` to a random ID type"""
    type_in = RemoteIDType.ID
    type_out = choice(ALL_ID_TYPES)
    return wrangler.convert(id_, kind=kind, type_in=type_in, type_out=type_out)


def random_id_types(
        wrangler: RemoteDataWrangler,
        kind: RemoteObjectType,
        id_list: Iterable[str] | None = None,
        start: int = 1,
        stop: int = 10
) -> list[str]:
    """Generate list of random ID types based on input item type"""
    if id_list:
        pass
    elif kind == RemoteObjectType.USER:
        id_list = [random_str() for _ in range(randrange(start=start, stop=stop))]
    else:
        id_list = random_ids(start=start, stop=stop)

    return [random_id_type(id_=id_, wrangler=wrangler, kind=kind) for id_ in id_list]
