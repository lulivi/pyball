import uuid

from typing import Optional

from peewee import CharField, IntegrityError, Model, SqliteDatabase, UUIDField

from pyball.greenfield.player.domain.errors import ErrorSavingPlayer
from pyball.greenfield.player.domain.model.player import Player as DomainPlayer
from pyball.greenfield.player.domain.players import Players
from pyball.greenfield.utils.peewee_db_wrapper import connection_wrapper
from pyball.settings import DATA_DIRECTORY_PATH

database = SqliteDatabase(DATA_DIRECTORY_PATH.joinpath("player.db"))


class Player(Model):
    """Player information."""

    id = UUIDField(null=False, unique=True)
    name = CharField(null=False, unique=True)

    class Meta:
        database = database  # Essto no funciona a ver si puedo meterlo aqui de alguna manera


class PlayerSqlitoRepository(Players):
    @connection_wrapper(database=database)
    def __init__(self) -> None:
        Player.create_table(safe=True)

    @connection_wrapper(database=database)
    def save(self, player: DomainPlayer) -> None:
        try:
            Player.create(id=player.id, name=player.name)
        except IntegrityError as error:
            raise ErrorSavingPlayer(player.id, player.name) from error

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
