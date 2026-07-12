class HttpNotFoundError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = 404
        self.error_type = "HTTP_NOT_FOUND"
