from src.controllers.interfaces.user_finder_controller_interface import (
    UserFinderControllerInterface,
)
from src.views.http_types.http_request import HttpRequest
from src.views.http_types.http_response import HttpResponse
from src.errors.error_handler import error_handler


class UserFinderView:
    def __init__(self, controller: UserFinderControllerInterface) -> None:
        self.__controller = controller

    async def handle(self, http_request: HttpRequest) -> HttpResponse:
        try:
            response = await self.__controller.find(
                user_id=http_request.path_params["user_id"],
                role=http_request.token_info["role"],
            )
            return HttpResponse(body=response, status_code=200)
        except Exception as e:  # pylint: disable=broad-except
            error_handler(e)
