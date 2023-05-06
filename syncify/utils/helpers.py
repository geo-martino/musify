from typing import Any, List, Optional


def make_list(data: Any) -> Optional[List]:
    if isinstance(data, list):
        return data
    elif isinstance(data, set):
        return list(data)

    return [data] if data is not None else None