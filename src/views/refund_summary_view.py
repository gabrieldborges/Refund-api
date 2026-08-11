from src.controllers.interfaces.refund_summary_controller_interface import (
    RefundSummaryControllerInterface,
)
from src.validators.refund_summary_validator import refund_summary_validator
from src.views.http_types.http_request import HttpRequest
from src.views.http_types.http_response import HttpResponse
from src.errors.error_handler import error_handler


class RefundSummaryView:
    def __init__(self, controller: RefundSummaryControllerInterface) -> None:
        self.__controller = controller

    async def handle(self, http_request: HttpRequest) -> HttpResponse:
        try:
            # Validator first, like RefundListerView: the bounds on `year` are
            # what keep an absurd value from reaching the repository — and from
            # building an invalid datetime in the controller.
            refund_summary_validator(http_request)

            response = await self.__controller.summarize(
                user_id=http_request.token_info["user_id"],
                role=http_request.token_info["role"],
                year=http_request.query.get("year"),
                filter_user_id=http_request.query.get("user_id"),
            )
            return HttpResponse(body=response, status_code=200)
        except Exception as e:  # pylint: disable=broad-except
            error_handler(e)
