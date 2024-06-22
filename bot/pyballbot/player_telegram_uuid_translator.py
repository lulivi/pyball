import uuid

from peewee import CharField, IntegrityError, Model, SqliteDatabase, UUIDField

from pyball.greenfield.utils.peewee_db_wrapper import connection_wrapper
from pyball.settings import DATA_DIRECTORY_PATH

database = SqliteDatabase(DATA_DIRECTORY_PATH.joinpath("telegram_player_translator.db"))


class TelegramPlayerTranslator(Model):
    id = UUIDField(null=False, unique=True)
    telegram_id = CharField(null=False, unique=True)

    class Meta:
        database = database  # Essto no funciona a ver si puedo meterlo aqui de alguna manera


class PlayerUuidNotFound(Exception):
    """"""

    def __init__(self, id: uuid.UUID) -> None:
        self.id = id
        self.message = f"The player's UUID `{id}` was not found"
        super().__init__(self.message)


class PlayerUuidAlreadyExistent(Exception):
    """There is a player with the same UUID in the Translator."""

    def __init__(self, id: uuid.UUID) -> None:
        self.id = id
        self.message = f"The player's UUID `{id}` is already in use"
        super().__init__(self.message)


class PlayerTelegramIdNotFound(Exception):
    """"""

    def __init__(self, telegram_id: str) -> None:
        self.telegram_id = telegram_id
        self.message = f"The player's Telegram ID `{telegram_id}` is was not found"
        super().__init__(self.message)


class PlayerTelegramIdInUse(Exception):
    """There is a player with the same UUID in the repository."""

    def __init__(self, telegram_id: str) -> None:
        self.telegram_id = telegram_id
        self.message = f"The player's Telegram ID `{telegram_id}` is already in use"
        super().__init__(self.message)


class TelegramPlayerTranslatorService:
    @connection_wrapper(database=database)
    def __init__(self) -> None:
        TelegramPlayerTranslator.create_table(safe=True)

    @connection_wrapper(database=database)
    def translate_telegram_id(self, telegram_id: str) -> uuid.UUID:
        try:
            return TelegramPlayerTranslator.get(
                TelegramPlayerTranslator.telegram_id == telegram_id
            ).id
        except TelegramPlayerTranslator.DoesNotExist as error:
            raise PlayerTelegramIdNotFound(
                f"Could not find the Telegram ID `{telegram_id}`"
            ) from error

    @connection_wrapper(database=database)
    def translate_uuid(self, id: uuid.UUID) -> str:
        try:
            return TelegramPlayerTranslator.get(TelegramPlayerTranslator.id == id).telegram_id
        except TelegramPlayerTranslator.DoesNotExist as error:
            raise PlayerUuidNotFound(f"Could not find the UUID `{id}`") from error

    @connection_wrapper(database=database)
    def save(self, id: uuid.UUID, telegram_id: str) -> None:
        if TelegramPlayerTranslator.get_or_none(id=id) is not None:
            raise PlayerUuidAlreadyExistent(id=id)
        if TelegramPlayerTranslator.get_or_none(telegram_id=telegram_id) is not None:
            raise PlayerTelegramIdInUse(telegram_id=telegram_id)

        TelegramPlayerTranslator.create(id=id, telegram_id=telegram_id)
