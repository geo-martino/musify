from typing import Any

from yarl import URL

from musify.types import UnitIterable
from musify.utils import to_collection


def format_url_log(method: str, url: URL, messages: UnitIterable[Any]) -> str:
    """Format a request for a given ``url`` of a given ``method`` appending the given ``messages``"""
    url = str(url.with_query(None))
    url_pad_map = [30, 40, 70, 100]
    url_pad = next((pad for pad in url_pad_map if len(url) < pad), url_pad_map[-1])

    return f"{method.upper():<7}: {url:<{url_pad}} | {" | ".join(map(str, to_collection(messages)))}"
