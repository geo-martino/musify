import pytest
from aioresponses import aioresponses
from faker import Faker


@pytest.fixture(scope="session")
def faker() -> Faker:
    """Sets up and yields a basic Faker object for fake data"""
    return Faker()


@pytest.fixture(scope="session")
def mock_response():
    with aioresponses() as m:
        yield m
