from musify.local._base import LocalResource
from musify.model.item.artist import Artist


class LocalArtist(LocalResource, Artist):
    pass
