from src.controllers.interfaces.user_lister_controller_interface import (
    UserListerControllerInterface,
)
from src.views.http_types.http_request import HttpRequest
from src.views.http_types.http_response import HttpResponse
from src.errors.error_handler import error_handler


class UserListerView:
    def __init__(self, controller: UserListerControllerInterface) -> None:
        self.__controller = controller

    async def handle(self, http_request: HttpRequest) -> HttpResponse:
        try:
            # No validator call here, unlike RefundListerView. The page and
            # per_page bounds are enforced by FastAPI's Query(ge=, le=) on the
            # route, and this endpoint has no whitelisted parameter: the order is
            # fixed at name ASC in the repository, so there is no set of allowed
            # values to express. A validator here would be copied shape with no
            # content.
            response = await self.__controller.list(
                page=http_request.query["page"],
                per_page=http_request.query["per_page"],
                role=http_request.token_info["role"],
                name=http_request.query.get("name"),
            )
            return HttpResponse(body=response, status_code=200)
        except Exception as e:  # pylint: disable=broad-except
            error_handler(e)
