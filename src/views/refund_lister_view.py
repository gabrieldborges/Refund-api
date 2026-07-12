from src.controllers.interfaces.refund_lister_controller_interface import (
    RefundListerControllerInterface,
)
from src.views.http_types.http_request import HttpRequest
from src.views.http_types.http_response import HttpResponse
from src.errors.error_handler import error_handler


class RefundListerView:
    def __init__(self, controller: RefundListerControllerInterface) -> None:
        self.__controller = controller

    async def handle(self, http_request: HttpRequest) -> HttpResponse:
        try:
            user_id = http_request.token_info["user_id"]
            role = http_request.token_info["role"]

            response = await self.__controller.list(
                page=http_request.query["page"],
                per_page=http_request.query["per_page"],
                name=http_request.query.get("name"),
                user_id=user_id,
                role=role,
            )
            return HttpResponse(body=response, status_code=200)
        except Exception as e:
            error_handler(e)
