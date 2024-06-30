import uuid

from typing import List, Optional

from peewee import BooleanField, CharField, IntegrityError, Model, SqliteDatabase, UUIDField

from pyball.player.domain.errors import (
    PlayerIdIsAlreadyInUse,
    PlayerNameIsAlreadyInUse,
    PlayerSaveError,
)
from pyball.player.domain.model.player import Player as DomainPlayer
from pyball.player.domain.players import Players
from pyball.settings import DATA_DIRECTORY_PATH
from pyball.utils.peewee_db_wrapper import connection_wrapper

database = SqliteDatabase(DATA_DIRECTORY_PATH.joinpath("player.db"))


class Player(Model):
    """Player information."""

    id = UUIDField(null=False, unique=True)
    name = CharField(null=False, unique=True)
    main = BooleanField(default=False)

    class Meta:
        database = database  # Essto no funciona a ver si puedo meterlo aqui de alguna manera


class PlayerSqlitoRepository(Players):
    @connection_wrapper(database=database)
    def __init__(self) -> None:
        Player.create_table(safe=True)

    @connection_wrapper(database=database)
    def save(self, player: DomainPlayer) -> None:
        try:
            Player.create(id=player.id, name=player.name, main=player.main)
        except IntegrityError as error:
            if "player.name" in str(error):
                raise PlayerNameIsAlreadyInUse(name=player.name)
            raise PlayerIdIsAlreadyInUse(id=player.id)

    @connection_wrapper(database=database)
    def all(self) -> List[Player]:
        return [
            Player(id=player.id, name=player.name, main=player.main) for player in Player.select()
        ]

    @connection_wrapper(database=database)
    def get(self, id: uuid.UUID) -> Optional[DomainPlayer]:
        try:
            player = Player.get(Player.id == id)
        except Player.DoesNotExist:
            return None
        return DomainPlayer(id=player.id, name=player.name)

    @connection_wrapper(database=database)
    def get_by_name(self, name: str) -> Optional[DomainPlayer]:
        try:
            player = Player.get(Player.name == name)
        except Player.DoesNotExist:
            return None
        return DomainPlayer(id=player.id, name=player.name)
