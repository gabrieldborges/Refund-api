from src.controllers.interfaces.avatar_remover_controller_interface import (
    AvatarRemoverControllerInterface,
)
from src.views.http_types.http_request import HttpRequest
from src.views.http_types.http_response import HttpResponse
from src.errors.error_handler import error_handler


class AvatarRemoverView:
    def __init__(self, controller: AvatarRemoverControllerInterface) -> None:
        self.__controller = controller

    async def handle(self, http_request: HttpRequest) -> HttpResponse:
        try:
            response = await self.__controller.remove(
                user_id=http_request.token_info["user_id"]
            )
            return HttpResponse(body=response, status_code=200)
        except Exception as e:
            error_handler(e)
