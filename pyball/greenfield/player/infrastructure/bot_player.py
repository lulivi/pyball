import uuid

from pyball.greenfield.player.application.create_player import CreatePlayer
from pyball.greenfield.player.domain.errors import (
    ErrorSavingPlayer,
    PlayerNameAlreadyInUseError,
    PlayerUuidAlreadyExistsError,
)
from pyball.greenfield.player.infrastructure.player_sqlite_repository import PlayerSqlitoRepository
from pyball.greenfield.utils.player_telegram_uuid_translator import (
    TelegramIdNotFound,
    TelegramPlayerTranslatorService,
    TranslationSaveError,
    UUIDNotFound,
)


def create_player(name: str, identifier: str, **_: dict):
    sqlito_repository = PlayerSqlitoRepository()
    new_player_id = uuid.uuid4()

    try:
        CreatePlayer(sqlito_repository).create(id=new_player_id, name=name)
    except (PlayerUuidAlreadyExistsError, PlayerNameAlreadyInUseError, ErrorSavingPlayer):
        pass  # Display error in telegram

    try:
        TelegramPlayerTranslatorService().save(id=new_player_id, telegram_id=identifier)
    except (TelegramIdNotFound, UUIDNotFound, TranslationSaveError):
        pass  # Display error in telegram
