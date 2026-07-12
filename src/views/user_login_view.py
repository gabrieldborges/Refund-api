from src.controllers.interfaces.user_login_controller_interface import UserLoginControllerInterface
from src.views.http_types.http_request import HttpRequest
from src.views.http_types.http_response import HttpResponse
from src.errors.error_handler import error_handler


class UserLoginView:
    def __init__(self, controller: UserLoginControllerInterface) -> None:
        self.__controller = controller

    async def handle(self, http_request: HttpRequest) -> HttpResponse:
        try:
            response = await self.__controller.login(http_request.body)
            return HttpResponse(body=response, status_code=200)
        except Exception as e:
            error_handler(e)
