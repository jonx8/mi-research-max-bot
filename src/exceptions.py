class BotException(Exception):
    """Базовое исключение бота"""
    pass


class SessionNotFoundError(BotException):
    def __init__(self, telegram_id: int):
        self.telegram_id = telegram_id
        super().__init__(f"Сессия для {telegram_id} не найдена")


class ValidationError(BotException):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


class InvalidStepError(BotException):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


class UserNotFoundError(BotException):
    def __init__(self, telegram_id: int = None):
        self.telegram_id = telegram_id
        super().__init__("Пользователь не найден")


class TechniqueNotFoundError(BotException):
    def __init__(self, technique_id: str = None):
        self.technique_id = technique_id
        super().__init__("Техника не найдена")


class CravingSessionNotFoundError(BotException):
    def __init__(self, telegram_id: int):
        self.telegram_id = telegram_id
        super().__init__(f"Сессия анализа тяги для {telegram_id} не найдена")