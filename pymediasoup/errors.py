class Error(Exception):
    """Base class for exceptions in this module."""

    pass


class UnsupportedError(Error):
    def __init__(self, message):
        self.message = message
        super().__init__(message)


class InvalidStateError(Error):
    def __init__(self, message):
        self.message = message
        super().__init__(message)
