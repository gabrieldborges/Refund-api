from src.controllers.interfaces.receipt_finder_controller_interface import (
    ReceiptFinderControllerInterface,
)
from src.views.http_types.http_request import HttpRequest
from src.views.http_types.http_response import HttpResponse
from src.errors.error_handler import error_handler


class ReceiptFinderView:
    def __init__(self, controller: ReceiptFinderControllerInterface) -> None:
        self.__controller = controller

    async def handle(self, http_request: HttpRequest) -> HttpResponse:
        try:
            response = await self.__controller.find(
                refund_id=http_request.path_params["refund_id"],
                user_id=http_request.token_info["user_id"],
                role=http_request.token_info["role"],
            )
            # The body carries raw bytes plus their media type instead of a JSON
            # dict: the route turns it into a binary Response, not a JSONResponse.
            return HttpResponse(body=response, status_code=200)
        except Exception as e:
            error_handler(e)
