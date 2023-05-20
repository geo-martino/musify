from syncify.utils import chunk


def test_chunk():
    flat = [1, 2, 3, 4, 5, 6, 7, 8]
    assert chunk(flat, 3) == [[1, 2, 3], [4, 5, 6], [7, 8]]
