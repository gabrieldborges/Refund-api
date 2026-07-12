from src.controllers.interfaces.refund_creator_controller_interface import (
    RefundCreatorControllerInterface,
)
from src.validators.refund_creator_validator import refund_creator_validator
from src.views.http_types.http_request import HttpRequest
from src.views.http_types.http_response import HttpResponse
from src.errors.error_handler import error_handler


class RefundCreatorView:
    def __init__(self, controller: RefundCreatorControllerInterface) -> None:
        self.__controller = controller

    async def handle(self, http_request: HttpRequest) -> HttpResponse:
        try:
            refund_creator_validator(http_request)
            user_id = http_request.token_info["user_id"]
            response = await self.__controller.create(http_request.body, user_id)
            return HttpResponse(body=response, status_code=201)
        except Exception as e:
            error_handler(e)
