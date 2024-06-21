import uuid

from typing import Optional

from peewee import CharField, IntegrityError, Model, SqliteDatabase, UUIDField

from pyball.greenfield.player.domain.errors import ErrorSavingPlayer
from pyball.greenfield.player.domain.model.player import Player as DomainPlayer
from pyball.greenfield.player.domain.players import Players
from pyball.settings import DATA_DIRECTORY_PATH


class PlayerSqlitoRepository(Players):
    database = SqliteDatabase(DATA_DIRECTORY_PATH.joinpath("greenfield_player.db"))

    class Player(database.Model):
        """Player information."""

        id = UUIDField(null=False, unique=True)
        name = CharField(null=False, unique=True)

    def __init__(self) -> None:
        self.database.connect()
        self.Player.create_table(safe=True)

    def save(self, player: DomainPlayer) -> None:
        try:
            self.Player.create(id=player.id, name=player.name)
        except IntegrityError as error:
            raise ErrorSavingPlayer(player.id, player.name) from error

    def get(self, id: uuid.UUID) -> Optional[DomainPlayer]:
        try:
            player = self.Player.get(self.Player.id == id)
        except self.Player.DoesNotExist:
            return None
        return DomainPlayer(id=player.id, name=player.name)

    def get_by_name(self, name: str) -> Optional[DomainPlayer]:
        try:
            player = self.Player.get(self.Player.name == name)
        except self.Player.DoesNotExist:
            return None
        return DomainPlayer(id=player.id, name=player.name)

    def __del__(self) -> None:
        self.database.close()
