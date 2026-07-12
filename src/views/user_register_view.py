from src.controllers.interfaces.user_register_controller_interface import (
    UserRegisterControllerInterface,
)
from src.views.http_types.http_request import HttpRequest
from src.views.http_types.http_response import HttpResponse
from src.errors.error_handler import error_handler


class UserRegisterView:
    def __init__(self, controller: UserRegisterControllerInterface) -> None:
        self.__controller = controller

    async def handle(self, http_request: HttpRequest) -> HttpResponse:
        try:
            response = await self.__controller.register(http_request.body)
            return HttpResponse(body=response, status_code=201)
        except Exception as e:
            error_handler(e)
