class InvalidAPI(Exception):
    """Ошибка ответа API сервера."""

    pass


class TokenError(Exception):
    """Ошибка проверки токена."""

    pass
