from musify.local._base import LocalResource
from musify.model.item.album import Album


class LocalAlbum(LocalResource, Album):
    pass
