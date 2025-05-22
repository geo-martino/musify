from musify.local._base import LocalResource
from musify.model.item.genre import Genre


class LocalGenre(LocalResource, Genre):
    pass
