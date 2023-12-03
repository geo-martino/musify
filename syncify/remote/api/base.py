from abc import ABCMeta, abstractmethod

from syncify.api import APIBase
from syncify.remote.processors.wrangle import RemoteDataWrangler


class RemoteAPIBase(APIBase, RemoteDataWrangler, metaclass=ABCMeta):

    @property
    @abstractmethod
    def api_url_base(self) -> str:
        """The base URL for making calls to the remote API"""
        raise NotImplementedError
