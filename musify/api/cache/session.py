from requests import Session, Request, Response

from musify.api.cache.backend.base import ResponseCache


class CachedSession(Session):

    __slots__ = ("cache",)

    def __init__(self, cache: ResponseCache):
        super().__init__()

        #: The cache to use when attempting to return a cached response.
        self.cache = cache

    def request(
            self,
            method,
            url,
            params=None,
            data=None,
            headers=None,
            cookies=None,
            files=None,
            auth=None,
            timeout=None,
            allow_redirects=True,
            proxies=None,
            hooks=None,
            stream=None,
            verify=None,
            cert=None,
            json=None,
    ):
        req = Request(
            method=method.upper(),
            url=url,
            headers=headers,
            files=files,
            data=data or {},
            json=json,
            params=params or {},
            auth=auth,
            cookies=cookies,
            hooks=hooks,
        )
        prep = self.prepare_request(req)
        cached_data = self.cache.get_response(prep)

        if cached_data:  # emulate a response object and return it
            if not isinstance(cached_data, str):
                repository = self.cache.get_repository_from_url(url)
                cached_data = repository.serialise(cached_data)

            response = Response()
            response.encoding = "utf-8"
            response._content = cached_data.encode(response.encoding)
            response.status_code = 200
            response.url = url
            response.request = prep

            return response

        return super().request(
            method,
            url,
            params=params,
            data=data,
            headers=headers,
            cookies=cookies,
            files=files,
            auth=auth,
            timeout=timeout,
            allow_redirects=allow_redirects,
            proxies=proxies,
            hooks=hooks,
            stream=stream,
            verify=verify,
            cert=cert,
            json=json,
        )
