from typing import Any
from collections.abc import Collection, Mapping

from syncify.spotify import __URL_AUTH__, __URL_API__

APIMethodInputType = str | Mapping[str, Any] | Collection[str] | list[Mapping[str, Any]]

# non-user authenticated access
AUTH_ARGS_BASIC = {
    "auth_args": {
        "url": f"{__URL_AUTH__}/api/token",
        "data": {
            "grant_type": "client_credentials",
            "client_id": "{client_id}",
            "client_secret": "{client_secret}",
        },
    },
    "user_args": None,
    "refresh_args": {
        "url": f"{__URL_AUTH__}/api/token",
        "data": {
            "grant_type": "refresh_token",
            "refresh_token": None,
            "client_id": "{client_id}",
            "client_secret": "{client_secret}",
        },
    },
    "test_expiry": 600,
    "token_file_path": "{token_file_path}",
    "token_key_path": ["access_token"],
    "header_extra": {"Accept": "application/json", "Content-Type": "application/json"},
}

# user authenticated access with scopes
AUTH_ARGS_USER = {
    "auth_args": {
        "url": f"{__URL_AUTH__}/api/token",
        "data": {
            "grant_type": "authorization_code",
            "code": None,
            "client_id": "{client_id}",
            "client_secret": "{client_secret}",
            "redirect_uri": "http://localhost:8080/",
        },
    },
    "user_args": {
        "url": f"{__URL_AUTH__}/authorize",
        "params": {
            "response_type": "code",
            "client_id": "{client_id}",
            "scope": " ".join(
                [
                    "playlist-modify-public",
                    "playlist-modify-private",
                    "playlist-read-collaborative",
                ]
            ),
            "redirect_uri": "http://localhost:8080/",
            "state": "syncify",
        },
    },
    "refresh_args": {
        "url": f"{__URL_AUTH__}/api/token",
        "data": {
            "grant_type": "refresh_token",
            "refresh_token": None,
            "client_id": "{client_id}",
            "client_secret": "{client_secret}",
        },
    },
    "test_args": {"url": f"{__URL_API__}/me"},
    "test_condition": lambda r: "href" in r and "display_name" in r,
    "test_expiry": 600,
    "token_file_path": "{token_file_path}",
    "token_key_path": ["access_token"],
    "header_extra": {"Accept": "application/json", "Content-Type": "application/json"},
}

