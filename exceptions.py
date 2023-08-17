class Error(Exception):
    """Базовый класс для исключений, которые не нужно отправлять в Telegram."""


class APIError(Exception):
    """API Exception."""

    pass


class HTTPRequestError(Exception):
    """HTTP Exception."""

    pass
