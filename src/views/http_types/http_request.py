class HttpRequest:
    def __init__(
        self,
        body: dict = None,
        headers: dict = None,
        path_params: dict = None,
        query: dict = None,
        token_info: dict = None,
    ) -> None:
        self.body = body
        self.headers = headers
        self.path_params = path_params
        self.query = query
        self.token_info = token_info
