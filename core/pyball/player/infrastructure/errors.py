class PlayerTelegramIdInUse(Exception):
    def __init__(self, telegram_id: str) -> None:
        self.telegram_id = telegram_id
        self.message = f"The player Telegram ID `{telegram_id}` is already in use"
        super().__init__(self.message)
