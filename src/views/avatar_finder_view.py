from src.controllers.interfaces.avatar_finder_controller_interface import (
    AvatarFinderControllerInterface,
)
from src.views.http_types.http_request import HttpRequest
from src.views.http_types.http_response import HttpResponse
from src.errors.error_handler import error_handler


class AvatarFinderView:
    def __init__(self, controller: AvatarFinderControllerInterface) -> None:
        self.__controller = controller

    async def handle(self, http_request: HttpRequest) -> HttpResponse:
        try:
            response = await self.__controller.find(
                user_id=http_request.path_params["user_id"]
            )
            return HttpResponse(body=response, status_code=200)
        except Exception as e:
            error_handler(e)
