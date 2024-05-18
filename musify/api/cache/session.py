from requests import Session, Request, Response, PreparedRequest

from musify.api.cache.backend.base import ResponseCache, ResponseRepository


class CachedSession(Session):
    """
    A modified session which attempts to get/save responses from/to a stored cache before/after sending it.

    :param cache: The cache to use for managing cached responses.
    """

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
            persist: bool = True
    ):
        """
        Constructs a :class:`Request <Request>` and prepares it.
        First attempts to find the response for the request in the cache and, if not found, sends it.
        If ``persist`` is True request was sent and matching cache repository was found and ,
        persist the response to the repository.
        Returns :class:`Response <Response>` object.

        :param method: method for the new :class:`Request` object.
        :param url: URL for the new :class:`Request` object.
        :param params: (optional) Dictionary or bytes to be sent in the query
            string for the :class:`Request`.
        :param data: (optional) Dictionary, list of tuples, bytes, or file-like
            object to send in the body of the :class:`Request`.
        :param json: (optional) json to send in the body of the
            :class:`Request`.
        :param headers: (optional) Dictionary of HTTP Headers to send with the
            :class:`Request`.
        :param cookies: (optional) Dict or CookieJar object to send with the
            :class:`Request`.
        :param files: (optional) Dictionary of ``'filename': file-like-objects``
            for multipart encoding upload.
        :param auth: (optional) Auth tuple or callable to enable
            Basic/Digest/Custom HTTP Auth.
        :param timeout: (optional) How long to wait for the server to send
            data before giving up, as a float, or a `(connect timeout,
            read timeout)` tuple.
        :type timeout: float or tuple
        :param allow_redirects: (optional) Set to True by default.
        :type allow_redirects: bool
        :param proxies: (optional) Dictionary mapping protocol or protocol and
            hostname to the URL of the proxy.
        :param hooks: Unknown.
        :param stream: (optional) whether to immediately download the response
            content. Defaults to ``False``.
        :param verify: (optional) Either a boolean, in which case it controls whether we verify
            the server's TLS certificate, or a string, in which case it must be a path
            to a CA bundle to use. Defaults to ``True``. When set to
            ``False``, requests will accept any TLS certificate presented by
            the server, and will ignore hostname mismatches and/or expired
            certificates, which will make your application vulnerable to
            man-in-the-middle (MitM) attacks. Setting verify to ``False``
            may be useful during local development or testing.
        :param cert: (optional) if String, path to ssl client cert file (.pem).
            If Tuple, ('cert', 'key') pair.
        :param persist: Whether to persist responses returned from sending network requests i.e. non-cached responses.
        :rtype: requests.Response
        """
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

        repository = self.cache.get_repository_from_requests(prep)
        response = self._get_cached_response(prep, repository=repository)

        if response is None:
            response = super().request(
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

            if persist and repository is not None:
                repository.save_response(response)

        return response

    def _get_cached_response(self, request: PreparedRequest, repository: ResponseRepository | None) -> Response | None:
        if repository is None:
            return

        cached_data = repository.get_response(request)
        if cached_data is None:
            return

        # emulate a response object and return it
        if not isinstance(cached_data, str):
            repository = self.cache.get_repository_from_url(request.url)
            cached_data = repository.serialize(cached_data)

        response = Response()
        response.encoding = "utf-8"
        response._content = cached_data.encode(response.encoding)
        response.status_code = 200
        response.url = request.url
        response.request = request

        return response
