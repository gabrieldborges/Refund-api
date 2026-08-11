from src.controllers.interfaces.refund_daily_counts_controller_interface import (
    RefundDailyCountsControllerInterface,
)
from src.validators.refund_daily_counts_validator import refund_daily_counts_validator
from src.views.http_types.http_request import HttpRequest
from src.views.http_types.http_response import HttpResponse
from src.errors.error_handler import error_handler


class RefundDailyCountsView:
    def __init__(self, controller: RefundDailyCountsControllerInterface) -> None:
        self.__controller = controller

    async def handle(self, http_request: HttpRequest) -> HttpResponse:
        try:
            # O validator devolve o mês já quebrado em ano e número, então esta view
            # não faz um segundo parse da mesma string.
            year, month = refund_daily_counts_validator(http_request)

            response = await self.__controller.count(
                user_id=http_request.token_info["user_id"],
                role=http_request.token_info["role"],
                year=year,
                month=month,
                filter_user_id=http_request.query.get("user_id"),
            )
            return HttpResponse(body=response, status_code=200)
        except Exception as e:  # pylint: disable=broad-except
            error_handler(e)
