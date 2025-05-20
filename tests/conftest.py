import pytest
from faker import Faker


@pytest.fixture(scope="session")
def faker() -> Faker:
    """Sets up and yields a basic Faker object for fake data"""
    return Faker()
