import pytest
from faker import Faker


@pytest.fixture
def images(faker: Faker) -> list[bytes]:
    return [faker.image() for _ in range(faker.random_int(3, 5))]
