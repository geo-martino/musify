import os
import shutil
from os.path import join, basename, dirname

import pytest
from _pytest.fixtures import SubRequest


@pytest.fixture
def path(request: pytest.FixtureRequest | SubRequest, tmp_path: str) -> str:
    """
    Copy the path of the source file to the test cache for this test and return the cache path.
    Deletes the test folder when test is done.
    """
    if hasattr(request, "param"):
        src_path = request.param
    else:  # assume path is given at the top-level fixture, get param from this request
        # noinspection PyProtectedMember
        src_path = request._pyfuncitem.callspec.params[request._parent_request.fixturename]

    trg_path = join(tmp_path, basename(src_path))

    os.makedirs(dirname(trg_path), exist_ok=True)
    shutil.copyfile(src_path, trg_path)

    yield trg_path

    shutil.rmtree(dirname(trg_path))
