# pylint: disable=duplicate-code
# Shares its handle() shape with ReceiptFinderView; the rule is deliberately
# identical, so a shared helper would be more machinery than the problem needs.
from src.controllers.interfaces.payment_receipt_finder_controller_interface import (
    PaymentReceiptFinderControllerInterface,
)
from src.views.http_types.http_request import HttpRequest
from src.views.http_types.http_response import HttpResponse
from src.errors.error_handler import error_handler


class PaymentReceiptFinderView:
    def __init__(self, controller: PaymentReceiptFinderControllerInterface) -> None:
        self.__controller = controller

    async def handle(self, http_request: HttpRequest) -> HttpResponse:
        try:
            response = await self.__controller.find(
                refund_id=http_request.path_params["refund_id"],
                user_id=http_request.token_info["user_id"],
                role=http_request.token_info["role"],
            )
            # Raw bytes plus media type: the route turns this into a binary
            # Response, not a JSONResponse.
            return HttpResponse(body=response, status_code=200)
        except Exception as e:
            error_handler(e)
