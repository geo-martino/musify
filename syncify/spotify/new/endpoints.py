from typing import Optional
from urllib.parse import urlparse

from spotify.helpers import SpotifyType, URIType
from syncify.utils.logger import Logger


class Endpoints(Logger):

    _user_id = None

    def convert(self, value: str, type_in: Optional[SpotifyType] = None, type_out: Optional[URIType] = None) -> str:
        """
        Converts id to required format - api/open URL, URI, or ID.

        :param value: URL/URI/ID to convert.
        :param type_in: Input ID type. Necessary when given value is simply an ID.
        :param type_out: Type of string to return.
        :return: Formatted string
        """
        value = value.strip()
        uri_types_str = [t.name.lower() for t in URIType]

        # url links always start with 'open'/'api'
        # URIs are always 3 strings separated by :
        url_check = urlparse(value.replace('/v1/', '/')).netloc.split(".")
        uri_check = value.split(':')

        if len(url_check) > 0 and url_check[0] == 'open' or url_check[0] == 'api':  # open/api url
            url_path = urlparse(value.replace('/v1/', '/')).path.split("/")
            type_str = [p for p in url_path if any(p.startswith(t) for t in uri_types_str)][0].rstrip('s')
            key = [p for p in url_path if len(p) == SpotifyType.URI.value][0]
        elif len(uri_check) == 3:  # URI
            type_str = uri_check[1]
            key = uri_check[2]
        elif type_in:  # use manually defined kind for a given id
            type_str = type_in.name.lower().rstrip('s')
            key = value
        else:
            self._logger.error("\33[91mID given but no 'kind' defined \33[0m")
            return value

        # reformat
        if type_out == 'api':
            out = f'{SpotifyType.API_URL}/{type_str}s/{key}'
        elif type_out == 'open':
            out = f'{SpotifyType.OPEN_URL}/{type_str}/{key}'
        elif type_out == 'uri':
            out = f'spotify:{type_str}:{key}'
        else:
            out = key

        return out
