class HttpUnauthorizedError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = 401
        self.error_type = "HTTP_UNAUTHORIZED"
