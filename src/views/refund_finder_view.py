# pylint: disable=duplicate-code
# Shares its 3-line "unpack refund_id/user_id/role" setup with RefundDeleterView; a
# shared helper would be more machinery than the problem needs for 3 dict lookups.
from src.controllers.interfaces.refund_finder_controller_interface import (
    RefundFinderControllerInterface,
)
from src.views.http_types.http_request import HttpRequest
from src.views.http_types.http_response import HttpResponse
from src.errors.error_handler import error_handler


class RefundFinderView:
    def __init__(self, controller: RefundFinderControllerInterface) -> None:
        self.__controller = controller

    async def handle(self, http_request: HttpRequest) -> HttpResponse:
        try:
            refund_id = http_request.path_params["refund_id"]
            user_id = http_request.token_info["user_id"]
            role = http_request.token_info["role"]

            response = await self.__controller.find(refund_id, user_id, role)
            return HttpResponse(body=response, status_code=200)
        except Exception as e:
            error_handler(e)
