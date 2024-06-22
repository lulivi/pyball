import logging
import uuid

from pyball.greenfield.player.application.create_player import CreatePlayer
from pyball.greenfield.player.domain import errors as domain_errors
from pyball.greenfield.player.infrastructure.errors import PlayerTelegramIdInUse
from pyball.greenfield.player.infrastructure.player_sqlito_repository import PlayerSqlitoRepository
from pyball.greenfield.utils.bot import player_telegram_uuid_translator as translator

logger = logging.getLogger(__name__)


def create_player(name: str, telegram_id: str) -> None:
    sqlito_repository = PlayerSqlitoRepository()
    new_player_id = uuid.uuid4()

    try:
        translator.TelegramPlayerTranslatorService().save(
            id=new_player_id, telegram_id=telegram_id
        )
    except translator.PlayerTelegramIdInUse as error:
        raise PlayerTelegramIdInUse(telegram_id=error.telegram_id)

    try:
        CreatePlayer(sqlito_repository).create(id=new_player_id, name=name)
    except (
        domain_errors.PlayerUuidAlreadyExistsError,
        domain_errors.PlayerNameAlreadyInUseError,
        domain_errors.ErrorSavingPlayer,
    ):
        pass  # Display error in telegram
