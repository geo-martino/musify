def make_list(data: object, default: list = None) -> list:
    if data is None:
        return default
    return data if isinstance(data, list) else [data]
