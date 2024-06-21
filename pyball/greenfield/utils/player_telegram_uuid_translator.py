import uuid

from peewee import CharField, IntegrityError, Model, SqliteDatabase, UUIDField

from pyball.settings import DATA_DIRECTORY_PATH


class TelegramIdNotFound(Exception):
    """"""


class UUIDNotFound(Exception):
    """"""


class TranslationSaveError(Exception):
    """"""


class TelegramPlayerTranslatorService:
    database = SqliteDatabase(DATA_DIRECTORY_PATH.joinpath("telegram_player_translator.db"))

    class TelegramPlayerTranslator(Model):
        id = UUIDField(null=False, unique=True)
        telegram_id = CharField(null=False, unique=True)

    def __init__(self) -> None:
        self.database.connect()
        self.TelegramPlayerTranslator.create_table(safe=True)

    def translate_telegram_id(self, telegram_id: str) -> uuid.UUID:
        try:
            return self.TelegramPlayerTranslator.get(
                self.TelegramPlayerTranslator.telegram_id == telegram_id
            ).id
        except self.TelegramPlayerTranslator.DoesNotExist as error:
            raise TelegramIdNotFound(f"Could not find the telegram ID `{telegram_id}`") from error

    def translate_uuid(self, id: uuid.UUID) -> str:
        try:
            return self.TelegramPlayerTranslator.get(
                self.TelegramPlayerTranslator.id == id
            ).telegram_id
        except self.TelegramPlayerTranslator.DoesNotExist as error:
            raise UUIDNotFound(f"Could not find the UUID `{id}`") from error

    def save(self, id: uuid.UUID, telegram_id: str) -> None:
        try:
            self.TelegramPlayerTranslator.create(id=id, telegram_id=telegram_id)
        except IntegrityError as error:
            raise TranslationSaveError(
                f"The uuid `{id}` or the telegram ID `{telegram_id}` already exist."
            ) from error
