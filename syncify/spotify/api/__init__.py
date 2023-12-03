from syncify import __PROGRAM_NAME__
from syncify.spotify import __URL_AUTH__, __URL_API__

# non-user authenticated access
API_AUTH_BASIC = {
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
API_AUTH_USER = {
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
            "state": __PROGRAM_NAME__,
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

