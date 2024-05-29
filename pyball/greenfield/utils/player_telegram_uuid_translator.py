import uuid

from typing import NamedTuple

from peewee import CharField, IntegrityError, SqliteDatabase, UUIDField

from pyball.greenfield.utils.db_base_model import BaseModel, database
from pyball.settings import DATA_DIRECTORY_PATH


class TelegramPlayerTranslator(BaseModel):
    id = UUIDField(null=False, unique=True)
    telegram_id = CharField(null=False, unique=True)


class TelegramIdNotFound(Exception):
    """"""


class UUIDNotFound(Exception):
    """"""


class TranslationSaveError(Exception):
    """"""


class TelegramPlayerTranslatorService:
    def __init__() -> None:
        database.initialize(
            SqliteDatabase(DATA_DIRECTORY_PATH.joinpath("telegram_player_translator.db"))
        )
        database.connect()
        TelegramPlayerTranslator.create_table(safe=True)

    def translate_telegram_id(telegram_id: str) -> uuid.UUID:
        try:
            return TelegramPlayerTranslator.get(
                TelegramPlayerTranslator.telegram_id == telegram_id
            ).id
        except TelegramPlayerTranslator.DoesNotExists as error:
            raise TelegramIdNotFound(f"Could not find the telegram ID `{telegram_id}`") from error

    def translate_uuid(id: uuid.UUID) -> str:
        try:
            return TelegramPlayerTranslator.get(TelegramPlayerTranslator.id == id).telegram_id
        except TelegramPlayerTranslator.DoesNotExists as error:
            raise UUIDNotFound(f"Could not find the UUID `{id}`") from error

    def save(id: uuid.UUID, telegram_id: str) -> None:
        try:
            TelegramPlayerTranslator.create(id=id, name=telegram_id)
        except IntegrityError as error:
            raise TranslationSaveError(
                f"The uuid `{id}` or the telegram ID `{telegram_id}` already exist."
            ) from error
