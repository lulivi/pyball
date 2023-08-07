"""Testing utils."""
import faker

from pyball import db

fake: faker.Faker = faker.Faker()


def create_wrapped_player(**kwargs) -> db.wrapper.Player:
    """Create a Player object."""
    return db.wrapper.Player(
        _id=kwargs.get("_id", fake.unique.random_int()),
        telegram_id=kwargs.get("telegram_id", fake.unique.random_int()),
        name=kwargs.get("name", fake.unique.name()),
        main=kwargs.get("main", True),
        **kwargs,
    )


def create_dict_player(**kwargs) -> dict:
    """Create a player as dictionary."""
    return {
        "telegram_id": kwargs.get("telegram_id", fake.unique.random_int()),
        "name": kwargs.get("name", fake.unique.name()),
        "main": kwargs.get("main", True),
        **kwargs,
    }
