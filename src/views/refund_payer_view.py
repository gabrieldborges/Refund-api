from src.controllers.interfaces.refund_payer_controller_interface import (
    RefundPayerControllerInterface,
)
from src.validators.refund_payer_validator import refund_payer_validator
from src.views.http_types.http_request import HttpRequest
from src.views.http_types.http_response import HttpResponse
from src.errors.error_handler import error_handler


class RefundPayerView:
    def __init__(self, controller: RefundPayerControllerInterface) -> None:
        self.__controller = controller

    async def handle(self, http_request: HttpRequest) -> HttpResponse:
        try:
            refund_payer_validator(http_request)

            response = await self.__controller.pay(
                refund_id=http_request.path_params["refund_id"],
                payer_id=http_request.token_info["user_id"],
                role=http_request.token_info["role"],
                filename=http_request.body["filename"],
                content=http_request.body["content"],
            )
            return HttpResponse(body=response, status_code=200)
        except Exception as e:
            error_handler(e)
