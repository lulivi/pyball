import uuid

from typing import List, Optional

from peewee import BooleanField, CharField, IntegrityError, Model, SqliteDatabase, UUIDField

from pyball.player.domain.errors import PlayerIdIsAlreadyInUse, PlayerNameIsAlreadyInUse
from pyball.player.domain.model.player import Player
from pyball.player.domain.players import Players
from pyball.settings import DATA_DIRECTORY_PATH
from pyball.utils.peewee_db_wrapper import connection_wrapper

database = SqliteDatabase(DATA_DIRECTORY_PATH.joinpath("player.db"))


class PlayerModel(Model):
    """Player information."""

    id = UUIDField(null=False, unique=True)
    name = CharField(null=False, unique=True)
    main = BooleanField(default=False)

    class Meta:
        database = database


class PlayerSqlitoRepository(Players):
    @connection_wrapper(database=database)
    def __init__(self) -> None:
        PlayerModel.create_table(safe=True)

    @connection_wrapper(database=database)
    def save(self, player: Player) -> None:
        try:
            PlayerModel.create(id=player.id, name=player.name, main=player.main)
        except IntegrityError as error:
            if "player.name" in str(error):
                raise PlayerNameIsAlreadyInUse(name=player.name)
            raise PlayerIdIsAlreadyInUse(id=player.id)

    @connection_wrapper(database=database)
    def all(self) -> List[Player]:
        return [
            Player(id=player.id, name=player.name, main=player.main)
            for player in PlayerModel.select()
        ]

    @connection_wrapper(database=database)
    def get(self, id: uuid.UUID) -> Optional[Player]:
        try:
            player = PlayerModel.get(PlayerModel.id == id)
        except PlayerModel.DoesNotExist:
            return None
        return Player(id=player.id, name=player.name)

    @connection_wrapper(database=database)
    def get_by_name(self, name: str) -> Optional[Player]:
        try:
            player = PlayerModel.get(PlayerModel.name == name)
        except PlayerModel.DoesNotExist:
            return None
        return Player(id=player.id, name=player.name)

    @connection_wrapper(database=database)
    def update(self, player: Player) -> int:
        return (
            PlayerModel.update(name=player.name, main=player.main)
            .where(PlayerModel.id == player.id)
            .execute()
        )

    @connection_wrapper(database=database)
    def delete(self, player: Player) -> int:
        return PlayerModel.delete().where(PlayerModel.id == player.id).execute()
