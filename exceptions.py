class IncorrectMessageError(Exception):
    """Класс кастомного исключения для send_message."""

    pass


class WrongAPIAnswerError(Exception):
    """Класс кастомного исключения для parse_status."""

    pass


class NoResponseReceivedError(Exception):
    """Класс кастомного исключения для get_api_answer."""

    pass


class FailAnswerConnectionError(Exception):
    """Класс кастомного исключения при ConnectionError."""

    pass
