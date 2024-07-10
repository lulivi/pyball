class BaseApiException(Exception):
    def __init__(self, status: int, message: str = "Unknown error", item: str = "unknown"):
        self.status = status
        self.message = message
        self.item = item
        super().__init__(self.message)


class PyballRedirection(BaseApiException):
    def __init__(
        self, status: int = 300, message: str = "Unknown redirection", item: str = "unknown"
    ):
        self.status = status
        self.message = message
        self.item = item
        super().__init__(self.message)


class PyballRedirectionNotModified(PyballRedirection):
    def __init__(self, object: str, item: str) -> None:
        super().__init__(status=304, message=f"The {object} was not modified")


class PyballClientError(Exception):
    def __init__(self, status: int = 400, message: str = "Unknown error", item: str = "unknown"):
        self.status = status
        self.message = message
        self.item = item
        super().__init__(self.message)


class PyballClientNotFound(PyballClientError):
    def __init__(self, object: str, item: str, value: str):
        super().__init__(
            status=404, message=f"Could not find the {object} by the {item} `{value}`", item=item
        )


class PyballClientConflict(PyballClientError):
    def __init__(self, object: str, item: str, value: str):
        super().__init__(
            status=409, message=f"Conflicted {object} by the {item} `{value}`", item=item
        )


class PyballClientUnprocessableContent(PyballClientError):
    def __init__(self, message: str, item: str):
        super().__init__(status=422, message=message, item=item)
