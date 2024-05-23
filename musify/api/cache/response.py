from asyncio import StreamReader

from aiohttp import ClientRequest, ClientResponse
# noinspection PyProtectedMember
from aiohttp.helpers import TimerNoop
from multidict import CIMultiDictProxy


class CachedResponse(ClientResponse):
    """Emulates :py:class:`ClientResponse` for a response found in a cache backed."""

    def __init__(self, request: ClientRequest, data: str | bytes):
        # noinspection PyTypeChecker,PyProtectedMember
        super().__init__(
            method=request.method,
            url=request.url,
            writer=None,
            continue100=None,
            timer=TimerNoop(),
            request_info=request.request_info,
            traces=[],
            loop=request.loop,
            session=request._session,
        )

        # response status
        self.version = request.version
        self.status = 200
        self.reason = "cached"

        # headers
        self._headers = CIMultiDictProxy(request.headers)
        self._raw_headers = ()

        self.content = StreamReader(loop=self._loop)

        if isinstance(data, str):
            data = data.encode()
        self.content.feed_data(data)
        self.content.feed_eof()
