import uuid

from typing import Optional

from peewee import CharField, IntegrityError, SqliteDatabase, UUIDField

from pyball.greenfield.player.domain.errors import ErrorSavingPlayer
from pyball.greenfield.player.domain.model.player import Player as DomainPlayer
from pyball.greenfield.player.domain.players import Players
from pyball.greenfield.utils.db_base_model import BaseModel, database
from pyball.settings import DATA_DIRECTORY_PATH


class Player(BaseModel):
    """Player information."""

    id = UUIDField(null=False, unique=True)
    name = CharField(null=False, unique=True)


class PlayerSqlitoRepository(Players):
    def __init__(self) -> None:
        database.initialize(SqliteDatabase(DATA_DIRECTORY_PATH.joinpath("players.db")))
        database.connect()
        Player.create_table(safe=True)

    def save(self, player: Player) -> None:
        try:
            Player.create(id=player.id, name=player.name)
        except IntegrityError as error:
            raise ErrorSavingPlayer(player.id, player.name) from error

    def get(self, id: uuid.UUID) -> Optional[Player]:
        try:
            player = Player.get(Player.id == id)
        except Player.DoesNotExists:
            return None
        return DomainPlayer(id=player.id, name=player.name)

    def get_by_name(self, name: str) -> Optional[Player]:
        try:
            player = Player.get(Player.name == name)
        except Player.DoesNotExists:
            return None
        return DomainPlayer(id=player.id, name=player.name)

    def __del__(self) -> None:
        database.close()
