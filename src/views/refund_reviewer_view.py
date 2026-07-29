from src.controllers.interfaces.refund_reviewer_controller_interface import (
    RefundReviewerControllerInterface,
)
from src.validators.refund_reviewer_validator import refund_reviewer_validator
from src.views.http_types.http_request import HttpRequest
from src.views.http_types.http_response import HttpResponse
from src.errors.error_handler import error_handler


class RefundReviewerView:
    def __init__(self, controller: RefundReviewerControllerInterface) -> None:
        self.__controller = controller

    async def handle(self, http_request: HttpRequest) -> HttpResponse:
        try:
            refund_reviewer_validator(http_request)

            response = await self.__controller.review(
                refund_id=http_request.path_params["refund_id"],
                reviewer_id=http_request.token_info["user_id"],
                role=http_request.token_info["role"],
                status=http_request.body["status"],
                reason=http_request.body.get("reason"),
            )
            return HttpResponse(body=response, status_code=200)
        except Exception as e:
            error_handler(e)
