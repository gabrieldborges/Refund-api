from src.controllers.interfaces.refund_stats_finder_controller_interface import (
    RefundStatsFinderControllerInterface,
)
from src.views.http_types.http_request import HttpRequest
from src.views.http_types.http_response import HttpResponse
from src.errors.error_handler import error_handler


class RefundStatsFinderView:
    def __init__(self, controller: RefundStatsFinderControllerInterface) -> None:
        self.__controller = controller

    async def handle(self, http_request: HttpRequest) -> HttpResponse:
        try:
            target_user_id = http_request.path_params["user_id"]
            user_id = http_request.token_info["user_id"]
            role = http_request.token_info["role"]

            response = await self.__controller.find(target_user_id, user_id, role)
            return HttpResponse(body=response, status_code=200)
        except Exception as e:
            error_handler(e)
