"""Testing utils."""
import faker

from pyball import db

fake: faker.Faker = faker.Faker()


def create_wrapped_player(**kwargs) -> db.wrapper.Player:
    """Create a Player object."""
    return db.wrapper.Player(
        id=kwargs.get("id", fake.unique.random_int()),
        telegram_id=kwargs.get("telegram_id", fake.unique.random_int()),
        name=kwargs.get("name", fake.unique.name()),
        main=kwargs.get("main", True),
        **kwargs,
    )


def create_dict_player(**kwargs) -> dict:
    """Create a player as dictionary."""
    return {
        "id": kwargs.get("id", fake.unique.random_int()),
        "telegram_id": kwargs.get("telegram_id", fake.unique.random_int()),
        "name": kwargs.get("name", fake.unique.name()),
        "main": kwargs.get("main", True),
        "rank": kwargs.get("rank", fake.random_int(max=10)),
    }


def create_dict_stats(player: int, **kwargs) -> dict:
    """Create player stats as dictionary."""
    return {
        "player": player,
        "goals": kwargs.get("goals", fake.random_int(max=50)),
        "assists": kwargs.get("assists", fake.random_int(max=50)),
        "wins": kwargs.get("wins", fake.random_int(max=10)),
        "losses": kwargs.get("losses", fake.random_int(max=10)),
        "ties": kwargs.get("ties", fake.random_int(max=10)),
        "skill": kwargs.get("skill", fake.random_int(max=100)),
    }
