class Error(Exception):
    """Base class for exceptions in this module."""
    pass

class UnsupportedError(Error):
    def __init__(self, message):
        self.message = message

class InvalidStateError(Error):
    def __init__(self, message):
        self.message = message