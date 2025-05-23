from random import choice

import pytest
from faker import Faker


@pytest.fixture
def images(faker: Faker) -> list[bytes]:
    return [
        faker.image(image_format=choice(["jpeg", "png"]))
        for _ in range(faker.random_int(3, 5))
    ]
